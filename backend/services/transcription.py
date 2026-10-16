import os
from faster_whisper import WhisperModel

# Use "base" by default for 4x faster CPU speed with high accuracy, or customize via .env
MODEL_SIZE = os.getenv("WHISPER_MODEL", "base")

_whisper_model = None

def get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        # Utilize 8 CPU threads for maximum throughput on multi-core systems
        _whisper_model = WhisperModel(
            MODEL_SIZE,
            device="cpu",
            compute_type="int8",
            cpu_threads=8
        )
    return _whisper_model

def transcribe_audio(audio_path: str) -> str:
    model = get_whisper_model()
    # beam_size=1 uses greedy decoding, running ~3-4x faster than beam_size=5
    segments, info = model.transcribe(audio_path, beam_size=1)
    
    transcript = ""
    for segment in segments:
        transcript += f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"

    return transcript
