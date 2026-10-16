import os
import cv2
import easyocr
from scenedetect import detect, ContentDetector

_reader = None

def get_reader():
    global _reader
    if _reader is None:
        _reader = easyocr.Reader(["en"])
    return _reader

def extract_slides_text(video_path: str, max_slides: int = 6) -> str:
    try:
        # Detect scenes with slightly higher threshold (32.0) to focus on distinct slides
        scene_list = detect(video_path, ContentDetector(threshold=32.0))
        if not scene_list:
            return ""

        # Limit to max_slides to keep CPU processing fast
        if len(scene_list) > max_slides:
            step = len(scene_list) // max_slides
            scene_list = [scene_list[i] for i in range(0, len(scene_list), step)][:max_slides]

        reader = get_reader()
        extracted_text = ""
        cap = cv2.VideoCapture(video_path)
        
        for i, scene in enumerate(scene_list):
            frame_idx = (scene[0].get_frames() + scene[1].get_frames()) // 2
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                # Downscale frame for 3x faster OCR inference on CPU
                h, w = frame.shape[:2]
                if w > 800:
                    scale = 800 / w
                    frame = cv2.resize(frame, (800, int(h * scale)))

                results = reader.readtext(frame, detail=0)
                text = " ".join(results)
                if text.strip():
                    extracted_text += f"\n[Slide {i+1}]: {text}\n"
                    
        cap.release()
        return extracted_text
    except Exception as e:
        print(f"Warning: Slide OCR extraction encountered an issue: {e}", flush=True)
        return ""
