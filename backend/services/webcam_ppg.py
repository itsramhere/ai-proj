"""
Real heart-rate sensing from the laptop webcam via remote photoplethysmography (rPPG).

Physiology: every heartbeat pushes a pulse of blood through the facial skin,
which modulates light absorption (strongest in the green band). Sampling a
face region at video frame rate therefore yields a weak periodic colour
signal from which the pulse frequency can be recovered spectrally.

Pipeline: webcam frames -> face ROI mean RGB -> POS chrominance projection
(Wang et al. 2017) -> FFT band-pass 0.7-3.5 Hz -> spectral peak -> BPM.

Honesty / privacy notes:
- Frames are processed in memory only: we keep one averaged (R, G, B) triple
  per frame; no image is ever stored or transmitted.
- The reader is optional and fail-soft: without a camera (or without OpenCV)
  BiometricAdaptiveEngine falls back to the emulated sensor stream and the
  telemetry reports heart_rate_source="emulated".
"""
import os
import threading
import time
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:  # OpenCV optional; the reader reports "no_camera" without it
    cv2 = None

# Camera & sampling configuration
CAMERA_INDEX = 0
CAPTURE_WIDTH = 320
CAPTURE_HEIGHT = 240

# DNN face detector (YuNet) model; optional, substantially improves ROI tracking
FACE_MODEL_PATH = Path(__file__).resolve().parent.parent / "assets" / "face_detection_yunet_2023mar.onnx"

# Spectral analysis configuration
WINDOW_SECONDS = 12.0        # rolling analysis window
MIN_WINDOW_SECONDS = 6.0     # minimum buffer before an estimate is attempted
MIN_FPS = 10.0               # below this the spectral estimate is not trusted
BAND_LOW_HZ = 0.7            # 42 BPM
BAND_HIGH_HZ = 3.5           # 210 BPM
ESTIMATE_INTERVAL_SEC = 1.0

# Face ROI sampling
FACE_DETECT_EVERY = 20       # frames between Haar cascades; ROI is reused/smoothed between
ROI_SMOOTHING = 0.35         # EMA factor for ROI drift

# Reading quality gate
CONFIDENCE_FLOOR = 0.20
MAX_READING_AGE_SEC = 10.0


def estimate_heart_rate(times: np.ndarray, frames_rgb: np.ndarray) -> dict | None:
    """
    Recovers heart rate from a window of per-frame mean RGB face samples.

    times:      1-D array of sample timestamps in seconds (sorted)
    frames_rgb: Nx3 array of per-frame mean (R, G, B) values

    Returns {"bpm", "confidence", "fps", "window_sec"} or None when the
    window is too short / too sparse for a trustworthy spectral estimate.
    """
    if len(times) < 2:
        return None
    duration = float(times[-1] - times[0])
    if duration < MIN_WINDOW_SECONDS:
        return None
    fps = (len(times) - 1) / duration
    if fps < MIN_FPS:
        return None

    # Resample onto a uniform grid at the measured frame rate (drops/jitter safe)
    grid = np.arange(times[0], times[-1], 1.0 / fps)
    r = np.interp(grid, times, frames_rgb[:, 0])
    g = np.interp(grid, times, frames_rgb[:, 1])
    b = np.interp(grid, times, frames_rgb[:, 2])

    # POS chrominance projection (motion / illumination robust)
    rn = r / (r.mean() + 1e-9)
    gn = g / (g.mean() + 1e-9)
    bn = b / (b.mean() + 1e-9)
    s1 = gn - bn
    s2 = gn + bn - 2.0 * rn
    alpha = float(s1.std() / (s2.std() + 1e-9))
    pulse = s1 + alpha * s2
    pulse = pulse - pulse.mean()

    n = len(pulse)
    freqs = np.fft.rfftfreq(n, d=1.0 / fps)
    power = np.abs(np.fft.rfft(pulse * np.hanning(n))) ** 2

    band = (freqs >= BAND_LOW_HZ) & (freqs <= BAND_HIGH_HZ)
    if band.sum() < 3:
        return None
    band_power = power[band]
    band_freqs = freqs[band]

    peak = int(np.argmax(band_power))
    f_peak = float(band_freqs[peak])
    # Sub-bin parabolic refinement around the peak
    if 0 < peak < len(band_power) - 1:
        y0, y1, y2 = band_power[peak - 1], band_power[peak], band_power[peak + 1]
        denom = y0 - 2.0 * y1 + y2
        if abs(denom) > 1e-12:
            delta = 0.5 * (y0 - y2) / denom
            f_peak += max(-0.5, min(0.5, float(delta))) * float(band_freqs[1] - band_freqs[0])

    # Confidence: share of in-band spectral energy concentrated at the peak
    lo = max(0, peak - 1)
    hi = min(len(band_power), peak + 2)
    confidence = float(band_power[lo:hi].sum() / (band_power.sum() + 1e-12))

    return {
        "bpm": round(f_peak * 60.0, 1),
        "confidence": round(confidence, 3),
        "fps": round(fps, 1),
        "window_sec": round(duration, 1),
    }


class WebcamPPGReader:
    """
    Background webcam sampler that produces live heart-rate readings.

    Runs a daemon thread that reads camera frames, tracks a face ROI, and
    keeps a rolling window of per-frame mean RGB triples. Once the window is
    long enough, POS + FFT yield a BPM estimate refreshed every second.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._user_disabled = False
        self._state = "idle"  # idle|starting|no_camera|warming_up|measuring|no_face|disabled|error
        self._last_error: str | None = None
        self._samples: list = []  # (timestamp, (r, g, b))
        self._buffer_sec = 0.0
        self._latest: dict | None = None

    # ------------------------------------------------------------------ API
    def auto_start(self):
        """Start sampling unless the user explicitly disabled the camera."""
        with self._lock:
            if self._user_disabled:
                return
            running = self._thread is not None and self._thread.is_alive()
        if not running:
            self.enable()

    def enable(self):
        with self._lock:
            self._user_disabled = False
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._state = "starting"
            self._last_error = None
            self._thread = threading.Thread(target=self._run, name="webcam-ppg", daemon=True)
            self._thread.start()

    def disable(self):
        with self._lock:
            self._user_disabled = True
            self._stop_event.set()
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=3.0)
        with self._lock:
            self._state = "disabled"
            self._samples.clear()
            self._latest = None
            self._buffer_sec = 0.0
        print("[Webcam rPPG] Reader disabled; emulated sensor stream active", flush=True)

    def reading(self) -> dict:
        """Latest estimate with freshness / quality info (thread-safe)."""
        with self._lock:
            latest = dict(self._latest) if self._latest else None
            state = self._state
            buffer_sec = self._buffer_sec
            error = self._last_error

        now = time.monotonic()
        out = {
            "state": state,
            "bpm": None,
            "confidence": None,
            "fps": None,
            "window_sec": None,
            "age_sec": None,
            "buffer_sec": buffer_sec,
            "usable": False,
            "reason": "no_reading_yet",
            "error": error,
        }
        if latest is not None:
            age = now - latest["timestamp"]
            out.update({
                "bpm": latest["bpm"],
                "confidence": latest["confidence"],
                "fps": latest["fps"],
                "window_sec": latest["window_sec"],
                "age_sec": round(age, 1),
            })
            if age > MAX_READING_AGE_SEC:
                out["reason"] = "stale"
            elif latest["confidence"] < CONFIDENCE_FLOOR:
                out["reason"] = "low_confidence"
            else:
                out["usable"] = True
                out["reason"] = "ok"
        elif state == "no_camera":
            out["reason"] = "no_camera"
        elif state == "disabled":
            out["reason"] = "disabled"
        return out

    # ------------------------------------------------------------- internals
    def _run(self):
        if cv2 is None:
            with self._lock:
                self._state = "no_camera"
                self._last_error = "OpenCV (cv2) is not installed in this environment"
            print("[Webcam rPPG] OpenCV not available; reader inactive", flush=True)
            return

        cap = self._open_capture()
        if cap is None:
            with self._lock:
                self._state = "no_camera"
                self._last_error = "no camera device could be opened"
            print("[Webcam rPPG] No camera device found; emulated heart rate will be used", flush=True)
            return

        detector = self._load_face_detector()
        mode = {
            "yunet": "YuNet DNN face detection",
            "haar": "Haar face detection",
        }.get(detector[0], "frame-centre fallback")
        print(
            f"[Webcam rPPG] Camera opened at {CAPTURE_WIDTH}x{CAPTURE_HEIGHT}; sampling via {mode} (frames stay in memory)",
            flush=True,
        )

        try:
            frame_idx = 0
            read_failures = 0
            face_box = None
            last_detect_frame = -FACE_DETECT_EVERY
            last_estimate_time = 0.0

            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok:
                    read_failures += 1
                    if read_failures > 30:
                        with self._lock:
                            self._state = "error"
                            self._last_error = "camera stopped delivering frames"
                        break
                    time.sleep(0.05)
                    continue
                read_failures = 0
                frame_idx += 1
                now = time.monotonic()

                if detector[0] is not None:
                    if face_box is None or (frame_idx - last_detect_frame) >= FACE_DETECT_EVERY:
                        face_box = self._detect_face(detector, frame, face_box)
                        last_detect_frame = frame_idx
                else:
                    h, w = frame.shape[:2]
                    face_box = (int(w * 0.30), int(h * 0.15), int(w * 0.40), int(h * 0.35))

                if face_box is not None:
                    x, y, w, h = face_box
                    # Forehead band: upper 40% of the box, central 60% width
                    fx1 = x + int(w * 0.20)
                    fx2 = x + int(w * 0.80)
                    fy1 = y + int(h * 0.10)
                    fy2 = y + int(h * 0.45)
                    roi = frame[fy1:fy2, fx1:fx2]
                    if roi.size > 0:
                        mean_bgr = roi.reshape(-1, 3).mean(axis=0)
                        # BGR -> RGB; store one averaged triple per frame
                        self._samples.append((now, (float(mean_bgr[2]), float(mean_bgr[1]), float(mean_bgr[0]))))
                        cutoff = now - (WINDOW_SECONDS + 2.0)
                        while self._samples and self._samples[0][0] < cutoff:
                            self._samples.pop(0)

                with self._lock:
                    if self._samples:
                        self._buffer_sec = round(self._samples[-1][0] - self._samples[0][0], 1)
                    if face_box is None:
                        self._state = "no_face"
                    elif self._buffer_sec < MIN_WINDOW_SECONDS:
                        self._state = "warming_up"
                    else:
                        self._state = "measuring"

                if (now - last_estimate_time) >= ESTIMATE_INTERVAL_SEC:
                    self._update_estimate(now)
                    last_estimate_time = now
        except Exception as exc:
            with self._lock:
                self._state = "error"
                self._last_error = str(exc)
            print(f"[Webcam rPPG] Reader error: {exc}", flush=True)
        finally:
            cap.release()

    def _open_capture(self):
        backends = []
        if os.name == "nt" and hasattr(cv2, "CAP_DSHOW"):
            backends.append(cv2.CAP_DSHOW)
        backends.append(getattr(cv2, "CAP_ANY", 0))
        for backend in backends:
            cap = cv2.VideoCapture(CAMERA_INDEX, backend)
            if cap.isOpened():
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
                # Let auto-exposure settle before sampling
                for _ in range(10):
                    cap.read()
                return cap
            cap.release()
        return None

    @staticmethod
    def _load_face_detector():
        """
        Prefers the DNN YuNet detector when the model file is present (works
        with OpenCV >= 4.5.4 and is the only bundled option in OpenCV 5.x,
        which no longer ships Haar cascade XMLs); falls back to Haar cascades
        and finally to frame-centre sampling. Returns (kind, detector).
        """
        if hasattr(cv2, "FaceDetectorYN") and FACE_MODEL_PATH.exists():
            logging_api = getattr(getattr(cv2, "utils", None), "logging", None)
            previous_level = None
            try:
                if logging_api is not None:
                    previous_level = logging_api.getLogLevel()
                    logging_api.setLogLevel(logging_api.LOG_LEVEL_SILENT)  # OpenCV 5's DNN graph engine is chatty at create time
                detector = cv2.FaceDetectorYN.create(str(FACE_MODEL_PATH), "", (0, 0), score_threshold=0.6)
                return "yunet", detector
            except Exception:
                pass
            finally:
                if previous_level is not None:
                    logging_api.setLogLevel(previous_level)
        try:
            path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            cascade = cv2.CascadeClassifier(path)
            if not cascade.empty():
                return "haar", cascade
        except Exception:
            pass
        return None, None

    def _detect_face(self, detector, frame, prev_box):
        kind, obj = detector
        if kind == "yunet":
            height, width = frame.shape[:2]
            obj.setInputSize((width, height))
            _, faces = obj.detect(frame)
            if faces is None or len(faces) == 0:
                return None
            best = max(faces, key=lambda face: float(face[2]) * float(face[3]))
            bx, by, bw, bh = (int(v) for v in best[:4])
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = obj.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(70, 70))
            if len(faces) == 0:
                return None
            bx, by, bw, bh = max(faces, key=lambda box: int(box[2]) * int(box[3]))

        if prev_box is None:
            return (bx, by, bw, bh)
        px, py, pw, ph = prev_box
        return (
            int(px + ROI_SMOOTHING * (bx - px)),
            int(py + ROI_SMOOTHING * (by - py)),
            int(pw + ROI_SMOOTHING * (bw - pw)),
            int(ph + ROI_SMOOTHING * (bh - ph)),
        )

    def _update_estimate(self, now: float):
        with self._lock:
            samples = list(self._samples)
        if len(samples) < 10:
            return
        times = np.array([s[0] for s in samples], dtype=np.float64)
        times -= times[0]
        frames_rgb = np.array([s[1] for s in samples], dtype=np.float64)
        estimate = estimate_heart_rate(times, frames_rgb)
        if estimate is None:
            return
        estimate["timestamp"] = now
        with self._lock:
            first = self._latest is None
            self._latest = estimate
        if first:
            print(
                f"[Webcam rPPG] First live heart-rate estimate: {estimate['bpm']} BPM (confidence {estimate['confidence']})",
                flush=True,
            )


# Process-wide singleton, mirroring the other hardware governors
webcam_ppg = WebcamPPGReader()
