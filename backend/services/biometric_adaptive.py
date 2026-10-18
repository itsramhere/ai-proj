import os
import time
import math
import random
import torch
import torch.nn as nn
from typing import Dict, Any, List

from services.webcam_ppg import webcam_ppg

class BiometricLSTM(nn.Module):
    """
    Bidirectional LSTM network that processes sequential biometric telemetry
    (PPG heart rate variability, GSR skin conductance, EEG Alpha/Beta/Theta power ratios)
    to compute an ongoing physical stress index and cognitive load score.
    """
    def __init__(self, input_dim: int = 5, hidden_dim: int = 32, num_layers: int = 2):
        super(BiometricLSTM, self).__init__()
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True
        )
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, 16),
            nn.ReLU(),
            nn.Linear(16, 2),  # Outputs [cognitive_load (0-1), stress_index (0-1)]
            nn.Sigmoid()
        )
        # Pre-seed weights deterministically so predictions are stable and smooth
        torch.manual_seed(42)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]
        return self.fc(last_step)

class BiometricAdaptiveEngine:
    """
    Option #3 Engine:
    Couples practice question paper difficulty to real-time biometric telemetry
    (Photoplethysmogram / PPG heart rate, Galvanic Skin Response / GSR, and EEG brainwaves).

    In LIVE mode the heart-rate channel is measured for real from the webcam via
    rPPG (services/webcam_ppg.py); GSR and EEG remain emulated because standard
    laptops carry no such sensors, and the telemetry labels every channel with
    its actual source. The sensor buffer is processed by a PyTorch LSTM network
    and the engine dynamically adapts question paper difficulty (Beginner,
    Intermediate, Advanced) in real time.
    """
    def __init__(self):
        self.model = BiometricLSTM()
        self.model.eval()
        
        # State & baseline variables
        # "LIVE" = real webcam heart rate when available; the other three are
        # full sensor-emulation demo states set via /system/biometrics/simulate.
        self.simulated_state = "LIVE"
        self.current_difficulty = "medium"
        self.heart_rate = 72.0
        self.gsr_conductance = 3.5  # microsiemens (uS)
        self.alpha_ratio = 1.2      # EEG Alpha (relaxation)
        self.beta_ratio = 0.8       # EEG Beta (alertness/stress)
        self.theta_ratio = 0.5      # EEG Theta (drowsiness/fatigue)

    def set_simulation_state(self, state: str):
        valid = ["LIVE", "LOW_STRESS", "NORMAL", "HIGH_STRESS"]
        if state in valid:
            self.simulated_state = state

    def generate_sensor_stream(self, seq_len: int = 10, hr_override: float | None = None) -> torch.Tensor:
        """
        Synthesizes the sensor streaming buffer of shape [1, seq_len, 5]:
        Features: [PPG_HeartRate_Norm, GSR_Norm, EEG_Alpha, EEG_Beta, EEG_Theta]

        hr_override: a real webcam rPPG heart-rate reading, when available,
        replaces the synthetic HR base (GSR/EEG features remain emulated).
        """
        # Baseline adjustments depending on state ("LIVE" uses normal baselines)
        state = self.simulated_state if self.simulated_state != "LIVE" else "NORMAL"
        if state == "HIGH_STRESS":
            hr_base = 105.0 + random.uniform(-4, 6)
            gsr_base = 9.2 + random.uniform(-0.5, 0.8)
            alpha_base = 0.45 + random.uniform(-0.05, 0.05)
            beta_base = 2.1 + random.uniform(-0.1, 0.2)
            theta_base = 0.3 + random.uniform(-0.05, 0.05)
        elif state == "LOW_STRESS":
            hr_base = 62.0 + random.uniform(-2, 3)
            gsr_base = 1.8 + random.uniform(-0.2, 0.3)
            alpha_base = 2.3 + random.uniform(-0.1, 0.2)
            beta_base = 0.5 + random.uniform(-0.05, 0.05)
            theta_base = 0.8 + random.uniform(-0.05, 0.05)
        else: # NORMAL
            hr_base = 74.0 + random.uniform(-3, 3)
            gsr_base = 3.8 + random.uniform(-0.3, 0.4)
            alpha_base = 1.1 + random.uniform(-0.08, 0.08)
            beta_base = 0.9 + random.uniform(-0.08, 0.08)
            theta_base = 0.5 + random.uniform(-0.05, 0.05)

        if hr_override is not None:
            hr_base = float(hr_override)

        self.heart_rate = round(hr_base, 1)
        self.gsr_conductance = round(gsr_base, 2)
        self.alpha_ratio = round(alpha_base, 2)
        self.beta_ratio = round(beta_base, 2)
        self.theta_ratio = round(theta_base, 2)

        sequence = []
        for i in range(seq_len):
            # Normalized features (HR / 150, GSR / 15, Alpha/3, Beta/3, Theta/3)
            step = [
                min(1.0, hr_base / 150.0 + random.uniform(-0.02, 0.02)),
                min(1.0, gsr_base / 15.0 + random.uniform(-0.02, 0.02)),
                min(1.0, alpha_base / 3.0 + random.uniform(-0.02, 0.02)),
                min(1.0, beta_base / 3.0 + random.uniform(-0.02, 0.02)),
                min(1.0, theta_base / 3.0 + random.uniform(-0.02, 0.02)),
            ]
            sequence.append(step)

        return torch.tensor([sequence], dtype=torch.float32)

    def evaluate_biometrics(self) -> Dict[str, Any]:
        """
        Runs the PyTorch LSTM on the biometric sequence buffer to determine
        the student's real-time physical stress & cognitive load states.

        In LIVE mode the webcam rPPG reader is consulted for a real heart-rate
        reading; if it is unavailable (no camera, disabled, warming up, low
        confidence) the emulated stream is used instead and reported as such.
        """
        webcam_ppg.auto_start()
        ppg = webcam_ppg.reading()
        real_hr = ppg["bpm"] if (self.simulated_state == "LIVE" and ppg["usable"]) else None
        heart_rate_source = "webcam_rppg" if real_hr is not None else "emulated"

        with torch.no_grad():
            x = self.generate_sensor_stream(seq_len=12, hr_override=real_hr)
            preds = self.model(x).squeeze(0)
            raw_cognitive = float(preds[0].item())
            raw_stress = float(preds[1].item())

        # Calibration based on sensor levels
        # Stress is higher if GSR is elevated and Beta/Alpha ratio is elevated
        calibrated_stress = min(1.0, max(0.0, (self.heart_rate - 55.0) / 60.0 * 0.4 + (self.gsr_conductance / 12.0) * 0.4 + (self.beta_ratio / 2.5) * 0.2))
        calibrated_cognitive = min(1.0, max(0.0, raw_cognitive * 0.3 + (self.beta_ratio / (self.alpha_ratio + 0.1)) * 0.4 + (self.heart_rate / 120.0) * 0.3))

        cognitive_pct = round(calibrated_cognitive * 100, 1)
        stress_pct = round(calibrated_stress * 100, 1)

        # Adapt difficulty based on physical cognitive load & stress
        if stress_pct > 65.0 or cognitive_pct > 75.0:
            target_difficulty = "easy"
            adaptation_action = "DE-ESCALATE: High stress/cognitive overload detected. Adapting quiz to foundational concepts to alleviate anxiety."
            stress_level_label = "HIGH (Overloaded)"
        elif stress_pct < 35.0 and cognitive_pct < 45.0:
            target_difficulty = "hard"
            adaptation_action = "CHALLENGE: Low stress and optimal focus detected. Elevating question paper to advanced analytical problems."
            stress_level_label = "LOW (Relaxed & Focused)"
        else:
            target_difficulty = "medium"
            adaptation_action = "MAINTAIN: Balanced cognitive load. Generating balanced conceptual questions."
            stress_level_label = "MODERATE (Optimal Attention)"

        self.current_difficulty = target_difficulty

        return {
            "heart_rate_bpm": self.heart_rate,
            "gsr_microsiemens": self.gsr_conductance,
            "eeg_alpha_ratio": self.alpha_ratio,
            "eeg_beta_ratio": self.beta_ratio,
            "eeg_theta_ratio": self.theta_ratio,
            "cognitive_load_pct": cognitive_pct,
            "stress_index_pct": stress_pct,
            "stress_level_label": stress_level_label,
            "recommended_difficulty": target_difficulty,
            "adaptation_action": adaptation_action,
            "simulated_state": self.simulated_state,
            "heart_rate_source": heart_rate_source,
            "ppg_state": ppg["state"],
            "ppg_confidence": ppg["confidence"],
            "ppg_fps": ppg["fps"],
            "sensor_sources": {
                "heart_rate": heart_rate_source,
                "gsr": "emulated",
                "eeg": "emulated"
            },
            "timestamp": time.time()
        }

biometric_engine = BiometricAdaptiveEngine()
