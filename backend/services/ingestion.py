import os
import subprocess
import yt_dlp
import uuid
import shutil
import glob

def download_video_and_extract_audio(url: str, output_dir: str = "./temp"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    video_id = str(uuid.uuid4())
    outtmpl_pattern = os.path.join(output_dir, f"{video_id}.%(ext)s")
    audio_path = os.path.join(output_dir, f"{video_id}.wav")

    # Download at max 720p: fast download & optimal resolution for OCR
    ydl_opts = {
        "format": "best[height<=720][ext=mp4]/bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "outtmpl": outtmpl_pattern,
        "quiet": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            title = info_dict.get("title", "Unknown Title")
            duration = info_dict.get("duration", 0)
            actual_video_path = ydl.prepare_filename(info_dict)
    except Exception as e:
        raise Exception(f"Failed to download video with yt-dlp: {e}")

    # If the extension differs (e.g. .mp4 vs .webm), locate the exact downloaded file
    if not os.path.exists(actual_video_path):
        matches = glob.glob(os.path.join(output_dir, f"{video_id}.*"))
        # Exclude audio file if already exists
        matches = [m for m in matches if not m.endswith(".wav")]
        if matches:
            actual_video_path = matches[0]
        else:
            raise Exception(f"Downloaded video file could not be found for ID: {video_id}")

    # Locate ffmpeg
    ffmpeg_bin = shutil.which("ffmpeg") or "ffmpeg"

    # Extract audio using ffmpeg: convert to 16kHz mono WAV (optimal for Whisper ASR)
    try:
        subprocess.run([
            ffmpeg_bin, "-i", actual_video_path, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", audio_path, "-y"
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
        raise Exception(f"Failed to extract audio with ffmpeg: {stderr_msg}")
    except FileNotFoundError:
        raise Exception("ffmpeg executable not found in system PATH.")

    return {
        "video_path": actual_video_path,
        "audio_path": audio_path,
        "title": title,
        "duration_sec": duration
    }
