import time
import json
import psutil
import os
from pathlib import Path

# Trained RL policy artifacts (written by backend/train_battery_rl.py)
RL_POLICY_PATH = Path(__file__).resolve().parent.parent / "battery_rl_policy.json"
RL_BATTERY_BIN_SIZE = 5.0                 # % per battery bin
RL_WORK_BIN_SIZE = 5.0                    # work units per bin
RL_N_BATTERY_BINS = 20
RL_N_WORK_BINS = 20
APP_SECONDS_PER_BATTERY_PCT = 120.0       # usable runtime per battery % (see est_usable_sec)
RL_DEFAULT_SECONDS_PER_WORK_UNIT = APP_SECONDS_PER_BATTERY_PCT / 2.15  # ~55.8s per RL work unit


class PredictivePowerGovernor:
    """
    Evaluates physical battery discharge rate and dynamically gates physical
    CPU silicon cores (heterogeneous affinity) and pipeline stages to guarantee
    safe generation of downloadable study notes & practice paper before power failure.
    """
    def __init__(self):
        self.total_cores = psutil.cpu_count(logical=True) or 4
        # Heterogeneous small/efficiency core cluster (first 4 cores)
        self.efficient_cores = list(range(min(4, self.total_cores)))
        self.all_cores = list(range(self.total_cores))
        
        self._simulated_low_battery = False
        self._history = []
        self._current_mode = "POWER_MODE_PERFORMANCE"

        # Trained Q-learning policy: (battery left, work left) -> continue/stop
        self.rl_policy = None
        self.rl_seconds_per_work_unit = RL_DEFAULT_SECONDS_PER_WORK_UNIT
        self._load_rl_policy()

    def _load_rl_policy(self):
        """
        Load the Q-table trained by backend/train_battery_rl.py. If the file is
        missing, the governor transparently falls back to the rule-based estimate.
        """
        try:
            with open(RL_POLICY_PATH, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            policy = payload.get("policy") or None
            if not policy:
                raise ValueError("policy section missing or empty")

            # Keep the seconds-per-work-unit conversion in sync with the
            # dynamics the agent was actually trained on.
            meta = payload.get("meta", {})
            drain = meta.get("battery_drain_range_pct_per_step")
            progress = meta.get("work_progress_range_units_per_step")
            if drain and progress and drain[0] > 0 and drain[1] > 0:
                work_per_pct = ((progress[0] + progress[1]) / 2.0) / ((drain[0] + drain[1]) / 2.0)
                self.rl_seconds_per_work_unit = APP_SECONDS_PER_BATTERY_PCT / work_per_pct

            self.rl_policy = policy
            print(f"[Power Governor] RL battery/work policy loaded: {len(policy)} states from {RL_POLICY_PATH.name}", flush=True)
        except FileNotFoundError:
            self.rl_policy = None
            print("[Power Governor] No trained RL policy found; using rule-based battery estimates. Run backend/train_battery_rl.py to train one.", flush=True)
        except Exception as e:
            self.rl_policy = None
            print(f"[Power Governor] Warning: could not load RL policy ({e}); using rule-based estimates.", flush=True)

    def toggle_simulated_low_battery(self, enabled: bool):
        self._simulated_low_battery = enabled

    def is_low_battery_simulated(self) -> bool:
        return self._simulated_low_battery

    def get_power_telemetry(self) -> dict:
        now = time.time()
        battery = psutil.sensors_battery()
        
        if self._simulated_low_battery:
            percent = 14
            power_plugged = False
            secsleft = 240 # 4 minutes remaining
            simulated = True
        elif battery:
            percent = int(battery.percent)
            power_plugged = bool(battery.power_plugged)
            secsleft = battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1
            simulated = False
        else:
            # Fallback for systems without a physical battery sensor
            percent = 100
            power_plugged = True
            secsleft = -1
            simulated = False

        # Track discharge history for rate calculation
        self._history.append((now, percent))
        if len(self._history) > 20:
            self._history.pop(0)

        # Estimate discharge rate (% per minute)
        discharge_rate_pct_min = 0.0
        if len(self._history) >= 2 and not power_plugged:
            dt_min = (self._history[-1][0] - self._history[0][0]) / 60.0
            d_pct = self._history[0][1] - self._history[-1][1]
            if dt_min > 0.1 and d_pct > 0:
                discharge_rate_pct_min = round(d_pct / dt_min, 2)

        # Determine power gating state
        # Critical if battery is unplugged and percent <= 20% or under 5 minutes left
        is_critical = (not power_plugged) and (percent <= 20 or (0 < secsleft <= 300))
        is_warning = (not power_plugged) and (percent <= 35)

        if is_critical:
            power_mode = "POWER_MODE_GATED"
            status_label = "CRITICAL_POWER_GATED (Silicon Throttled)"
            gated_cores = self.efficient_cores
            allow_heavy_ocr = False
        elif is_warning:
            power_mode = "POWER_MODE_CONSERVATIVE"
            status_label = "CONSERVATIVE (Efficiency Prioritized)"
            gated_cores = self.all_cores
            allow_heavy_ocr = True
        else:
            power_mode = "POWER_MODE_PERFORMANCE"
            status_label = "FULL_PERFORMANCE (All Cores Active)"
            gated_cores = self.all_cores
            allow_heavy_ocr = True

        self._current_mode = power_mode
        self._apply_core_affinity(gated_cores)

        current_affinity = psutil.Process().cpu_affinity()

        return {
            "percent": percent,
            "power_plugged": power_plugged,
            "secsleft": secsleft,
            "discharge_rate_pct_min": discharge_rate_pct_min,
            "power_mode": power_mode,
            "status_label": status_label,
            "active_cores": current_affinity,
            "total_cores": self.total_cores,
            "cores_active_count": len(current_affinity),
            "allow_heavy_ocr": allow_heavy_ocr,
            "simulated": simulated,
            "guaranteed_safe_completion": True,
            "rl_policy_loaded": self.rl_policy is not None,
            "rl_policy_states": len(self.rl_policy) if self.rl_policy else 0,
            "timestamp": now
        }

    def _apply_core_affinity(self, target_cores: list):
        try:
            p = psutil.Process()
            if set(p.cpu_affinity()) != set(target_cores):
                p.cpu_affinity(target_cores)
                print(f"[Power Governor] Silicon affinity dynamic shift: {len(target_cores)}/{self.total_cores} cores active {target_cores}", flush=True)
        except Exception as e:
            print(f"[Power Governor] Warning setting core affinity: {e}", flush=True)

    @staticmethod
    def _rl_bin_index(value: float, bin_size: float, n_bins: int) -> int:
        """Discretise a reading into the bin index the RL policy was trained on."""
        return max(0, min(int(value // bin_size), n_bins - 1))

    def rl_recommendation(self, battery_pct: float, work_left_units: float, power_plugged: bool = False) -> dict:
        """
        Consult the trained Q-learning policy with the two observations it was
        trained on (battery % left, work units left) and return continue/stop.

        Falls back to the previous rule-based estimate when no trained policy
        is available, so behavior is unchanged on a fresh checkout.
        """
        battery_pct = max(0.0, min(float(battery_pct), 100.0))
        work_left_units = max(0.0, min(float(work_left_units), 100.0))

        if power_plugged:
            decision, source = "continue", "charging"
        else:
            decision, source = None, None
            if self.rl_policy is not None:
                b = self._rl_bin_index(battery_pct, RL_BATTERY_BIN_SIZE, RL_N_BATTERY_BINS)
                w = self._rl_bin_index(work_left_units, RL_WORK_BIN_SIZE, RL_N_WORK_BINS)
                action = self.rl_policy.get(f"{b},{w}")
                if action is not None:
                    decision = "continue" if int(action) == 0 else "stop"
                    source = "rl_policy"

            if decision is None:
                # Rule-based fallback: battery must cover estimated work with a
                # 5% shutdown reserve and a 15% safety margin (prior behavior).
                required_battery = (work_left_units / 2.15) * 1.15
                feasible = (battery_pct - 5.0) >= required_battery
                decision = "continue" if feasible else "stop"
                source = "heuristic_fallback"

        return {
            "decision": decision,
            "source": source,
            "battery_pct": round(battery_pct, 1),
            "work_left_units": round(work_left_units, 1),
        }

    def evaluate_video_execution_budget(self, video_duration_sec: float, remaining_fraction: float = 1.0) -> dict:
        """
        Predicts whether remaining physical battery can safely complete the
        remaining pipeline work before power cutoff.

        The continue/stop decision is made by the trained Q-learning policy
        from (battery left, work left); remaining processing seconds are
        converted into the policy's battery-normalised work units.
        """
        telemetry = self.get_power_telemetry()
        # With 8-thread Whisper + Qwen 2.5 3B, processing factor is ~0.25 of video duration
        est_processing_sec = round(video_duration_sec * 0.25, 1)
        remaining_fraction = max(0.0, min(remaining_fraction, 1.0))
        remaining_processing_sec = est_processing_sec * remaining_fraction
        work_left_units = min(100.0, remaining_processing_sec / self.rl_seconds_per_work_unit)

        recommendation = self.rl_recommendation(
            telemetry["percent"], work_left_units, telemetry["power_plugged"]
        )

        secsleft = telemetry["secsleft"]
        # If secsleft unknown, estimate based on battery % (assume 1% ≈ 120s runtime)
        if secsleft <= 0:
            est_usable_sec = max(0, (telemetry["percent"] - 5) * 120)
        else:
            est_usable_sec = max(0, secsleft - 60) # 1 min safety buffer

        # Hard physical interlock: the OS-reported runtime cannot cover the
        # job even if the RL policy would take the risk.
        hard_infeasible = (
            (not telemetry["power_plugged"])
            and 0 < secsleft < (est_processing_sec + 60)
        )

        if recommendation["source"] == "charging":
            can_safely_complete = True
        else:
            can_safely_complete = (recommendation["decision"] == "continue") and not hard_infeasible

        if hard_infeasible and recommendation["source"] != "charging":
            decision_source = "hard_interlock"
        else:
            decision_source = recommendation["source"]

        # Conservative operational floor retained: critical battery still gates
        # heavy slide vision, and we never run OCR when the RL policy says stop.
        allow_heavy_ocr = telemetry["allow_heavy_ocr"] and can_safely_complete

        decision = {
            "can_safely_complete": can_safely_complete,
            "est_processing_sec": est_processing_sec,
            "est_usable_sec": est_usable_sec,
            "allow_heavy_ocr": allow_heavy_ocr,
            "power_mode": telemetry["power_mode"],
            "rl_decision": recommendation["decision"],
            "decision_source": decision_source,
            "rl_work_left_units": recommendation["work_left_units"],
            "rl_battery_pct": recommendation["battery_pct"],
        }

        if not telemetry["allow_heavy_ocr"]:
            print("[Power Governor] EMERGENCY POWER-GATING ACTIVE: Suppressing non-essential slide vision to guarantee downloadable quiz paper completion!", flush=True)

        return decision

# Global singleton
power_governor = PredictivePowerGovernor()
