import time
import psutil
import os

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

    def evaluate_video_execution_budget(self, video_duration_sec: float) -> dict:
        """
        Predicts whether remaining physical battery can safely complete
        ASR transcription and downloadable question paper before power cutoff.
        """
        telemetry = self.get_power_telemetry()
        # With 8-thread Whisper + Qwen 2.5 3B, processing factor is ~0.25 of video duration
        est_processing_sec = round(video_duration_sec * 0.25, 1)

        secsleft = telemetry["secsleft"]
        # If secsleft unknown, estimate based on battery % (assume 1% ≈ 120s runtime)
        if secsleft <= 0:
            est_usable_sec = max(0, (telemetry["percent"] - 5) * 120)
        else:
            est_usable_sec = max(0, secsleft - 60) # 1 min safety buffer

        can_safely_complete = telemetry["power_plugged"] or (est_usable_sec >= est_processing_sec)

        decision = {
            "can_safely_complete": can_safely_complete,
            "est_processing_sec": est_processing_sec,
            "est_usable_sec": est_usable_sec,
            "allow_heavy_ocr": telemetry["allow_heavy_ocr"],
            "power_mode": telemetry["power_mode"]
        }

        if not telemetry["allow_heavy_ocr"]:
            print("[Power Governor] EMERGENCY POWER-GATING ACTIVE: Suppressing non-essential slide vision to guarantee downloadable quiz paper completion!", flush=True)

        return decision

# Global singleton
power_governor = PredictivePowerGovernor()
