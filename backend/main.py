import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import os
import time

from database import engine, Base, get_db, SessionLocal
from models import models
from services.ingestion import download_video_and_extract_audio
from services.transcription import transcribe_audio
from services.llm import generate_notes, generate_diagrams, generate_quiz
from services.ocr import extract_slides_text
from services.charts import extract_and_plot_trends
from services.rag import RAGStore
from services.export import export_markdown_to_pdf

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Lecture Video Analyzer")

# Enable CORS for frontend requests (e.g. from Vite on port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

class AnalyzeRequest(BaseModel):
    url: str
    
class ChatRequest(BaseModel):
    lecture_id: int
    question: str

def process_video_task(url: str):
    db = SessionLocal()
    start_time = time.time()
    try:
        print(f"\n==========================================", flush=True)
        print(f"[>] Starting analysis for: {url}", flush=True)
        
        # Step 1: Download & Extract
        print("[1/4] Downloading video & extracting audio...", flush=True)
        media_info = download_video_and_extract_audio(url)
        print(f"      Title: '{media_info['title']}' ({media_info['duration_sec']}s)", flush=True)
        
        # Predictive Power-Gating Evaluation (trained RL policy governs the decision)
        power_budget = power_governor.evaluate_video_execution_budget(media_info["duration_sec"])
        print(f"[Power Governor] Battery Mode: {power_budget['power_mode']} | Usable Energy: {power_budget['est_usable_sec']}s vs Needed: {power_budget['est_processing_sec']}s", flush=True)
        print(f"[Power Governor] RL Decision: {power_budget['rl_decision'].upper()} (source: {power_budget['decision_source']} | battery: {power_budget['rl_battery_pct']}% | work left: {power_budget['rl_work_left_units']} units)", flush=True)

        # Step 2: Transcribe
        print("[2/4] Transcribing audio with Whisper ASR...", flush=True)
        transcript = transcribe_audio(media_info["audio_path"])
        print(f"      Transcription complete! ({len(transcript)} characters)", flush=True)
        
        # Step 3: Slide extraction (power-gated if on critical battery)
        if power_budget["allow_heavy_ocr"]:
            print("[3/4] Extracting slide text via OCR...", flush=True)
            slide_text = extract_slides_text(media_info["video_path"])
            print("      Slide OCR complete!", flush=True)
        else:
            print("[3/4] [Power-Gated] Suppressing heavy slide vision to guarantee downloadable question paper before power cutoff!", flush=True)
            slide_text = "[Notice: Slide vision gated under critical battery state to guarantee practice quiz generation before power failure.]"
        full_transcript = transcript + "\n\n" + slide_text
        
        # Save lecture to DB
        new_lecture = models.Lecture(
            source_url=url,
            title=media_info["title"],
            transcript=full_transcript,
            duration_sec=media_info["duration_sec"]
        )
        db.add(new_lecture)
        db.commit()
        db.refresh(new_lecture)
        
        # Step 4: Notes, Diagrams, Quiz via LM Studio
        print("[4/4] Generating notes, diagrams, and quiz via LM Studio...", flush=True)
        notes_content = generate_notes(full_transcript)
        print("      Notes generated!", flush=True)
        
        diagrams_content = generate_diagrams(full_transcript)
        print("      Diagrams generated!", flush=True)
        
        charts_content = extract_and_plot_trends(full_transcript)
        
        final_markdown = notes_content
        if charts_content:
            final_markdown += "\n\n## Charts\n" + charts_content
            
        new_note = models.Note(
            lecture_id=new_lecture.id,
            content_markdown=final_markdown,
            diagrams=diagrams_content
        )
        db.add(new_note)
        
        quiz_json = generate_quiz(full_transcript)
        new_quiz = models.Quiz(
            lecture_id=new_lecture.id,
            questions=quiz_json
        )
        db.add(new_quiz)
        
        db.commit()
        elapsed = round(time.time() - start_time, 1)
        print(f"[SUCCESS] Analysis finished successfully in {elapsed}s! Saved to database.", flush=True)
        print(f"==========================================\n", flush=True)
        
        # Cleanup temporary files
        if os.path.exists(media_info["video_path"]):
            os.remove(media_info["video_path"])
        if os.path.exists(media_info["audio_path"]):
            os.remove(media_info["audio_path"])
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"\n[ERROR] Error processing video: {e}", flush=True)
    finally:
        db.close()

@app.post("/analyze")
def analyze_video(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_video_task, request.url)
    return {"message": "Video processing started in background."}

@app.get("/lectures")
def get_lectures(db: Session = Depends(get_db)):
    return db.query(models.Lecture).all()

@app.get("/lectures/{lecture_id}/notes")
def get_notes(lecture_id: int, db: Session = Depends(get_db)):
    note = db.query(models.Note).filter(models.Note.lecture_id == lecture_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notes not found")
    return note

@app.get("/lectures/{lecture_id}/quiz")
def get_quiz(lecture_id: int, db: Session = Depends(get_db)):
    quiz = db.query(models.Quiz).filter(models.Quiz.lecture_id == lecture_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz

# Simple cache for RAG stores per lecture
rag_stores = {}

@app.post("/chat")
def chat_with_lecture(request: ChatRequest, db: Session = Depends(get_db)):
    lecture = db.query(models.Lecture).filter(models.Lecture.id == request.lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
        
    if request.lecture_id not in rag_stores:
        store = RAGStore()
        store.add_document(lecture.transcript)
        rag_stores[request.lecture_id] = store
        
    store = rag_stores[request.lecture_id]
    answer = store.query(request.question)
    
    # Save chat log
    chat_log_user = models.ChatLog(lecture_id=lecture.id, role="user", message=request.question)
    chat_log_assistant = models.ChatLog(lecture_id=lecture.id, role="assistant", message=answer)
    db.add(chat_log_user)
    db.add(chat_log_assistant)
    db.commit()
    
    return {"answer": answer}

@app.get("/lectures/{lecture_id}/export")
def export_notes_pdf(lecture_id: int, db: Session = Depends(get_db)):
    note = db.query(models.Note).filter(models.Note.lecture_id == lecture_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Notes not found")
        
    pdf_path = export_markdown_to_pdf(note.content_markdown)
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"lecture_{lecture_id}_notes.pdf")

from services.thermal_agent import thermal_agent

class SpikeSimulationRequest(BaseModel):
    simulate: bool

class PhysicalStressRequest(BaseModel):
    enabled: bool

@app.get("/system/thermal")
def get_system_thermal():
    """
    Returns live physical thermal sensor readings, CPU power state, and RL agent model decision.
    """
    decision = thermal_agent.select_model()
    return decision

@app.post("/system/thermal/simulate-spike")
def toggle_thermal_spike(request: SpikeSimulationRequest):
    """
    Demonstration trigger: Simulates a physical thermal throttling spike to demonstrate the RL agent's dynamic fallback.
    """
    thermal_agent.sensor.toggle_simulated_spike(request.simulate)
    return {
        "message": f"Thermal spike simulation {'enabled (82.5 C)' if request.simulate else 'disabled (normal sensor readings)'}",
        "simulated": request.simulate
    }

@app.post("/system/thermal/physical-stress")
def toggle_physical_stress(request: PhysicalStressRequest):
    """
    Hardware stress trigger: Spins multi-core matrix computation threads on real CPU cores,
    forcing genuine electrical wattage consumption and physical hardware temperature elevation!
    """
    active = thermal_agent.sensor.toggle_physical_stress(request.enabled)
    return {
        "message": f"Physical hardware CPU stress burn {'started (100% Core Load)' if active else 'stopped'}",
        "physical_stress_active": active
    }

from services.power_governor import power_governor

class PowerSimulationRequest(BaseModel):
    simulate: bool

@app.get("/system/power")
def get_system_power():
    """
    Returns live physical battery discharge telemetry, core affinity mask, and predictive power-gating state.
    """
    return power_governor.get_power_telemetry()

@app.post("/system/power/simulate-discharge")
def toggle_power_simulation(request: PowerSimulationRequest):
    """
    Demonstration trigger: Simulates a critical battery discharge state (<15% unplugged)
    to demonstrate dynamic silicon core power-gating and workload assurance.
    """
    power_governor.toggle_simulated_low_battery(request.simulate)
    return {
        "message": f"Battery discharge simulation {'enabled (14% on battery, core power-gated)' if request.simulate else 'disabled (normal physical battery metrics)'}",
        "simulated": request.simulate
    }

from services.biometric_adaptive import biometric_engine
from services.webcam_ppg import webcam_ppg

class BiometricSimulationRequest(BaseModel):
    state: str # "LIVE", "LOW_STRESS", "NORMAL", "HIGH_STRESS"

class BiometricCameraRequest(BaseModel):
    enabled: bool

class RegenerateQuizRequest(BaseModel):
    difficulty: str | None = None # "easy", "medium", "hard" or None (auto-detect from biometrics)

@app.get("/system/biometrics")
def get_biometric_telemetry():
    """
    Returns real-time biometric telemetry. Heart rate is measured live from the
    webcam via rPPG when available (emulated fallback otherwise); GSR and EEG
    channels are emulated and labelled as such in sensor_sources.
    """
    return biometric_engine.evaluate_biometrics()

@app.post("/system/biometrics/camera")
def set_biometric_camera(request: BiometricCameraRequest):
    """
    Enables/disables the webcam rPPG heart-rate reader. Frames are processed
    in memory only (per-frame face-region colour averages) and never stored.
    """
    if request.enabled:
        webcam_ppg.enable()
        message = "Webcam rPPG reader enabled - allow a few seconds to warm up"
    else:
        webcam_ppg.disable()
        message = "Webcam rPPG reader disabled - emulated heart rate active"
    return {
        "message": message,
        "ppg": webcam_ppg.reading()
    }

@app.post("/system/biometrics/simulate")
def set_biometric_simulation(request: BiometricSimulationRequest):
    """
    Switches the biometric sensor mode. "LIVE" uses the real webcam heart-rate
    reading; LOW_STRESS / NORMAL / HIGH_STRESS are full sensor-emulation demo
    states for testing dynamic question paper adaptation without wearables.
    """
    biometric_engine.set_simulation_state(request.state)
    return {
        "message": f"Biometric state switched to: {request.state}",
        "telemetry": biometric_engine.evaluate_biometrics()
    }

@app.post("/lectures/{lecture_id}/quiz/adapt")
def adapt_lecture_quiz(lecture_id: int, request: RegenerateQuizRequest, db: Session = Depends(get_db)):
    """
    Dynamically generates or adapts the practice question paper difficulty
    based on the student's physical cognitive load and stress state.
    """
    lecture = db.query(models.Lecture).filter(models.Lecture.id == lecture_id).first()
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")

    bio_status = biometric_engine.evaluate_biometrics()
    target_diff = request.difficulty or bio_status["recommended_difficulty"]

    # Generate new quiz tailored to cognitive load
    quiz_json = generate_quiz(lecture.transcript, difficulty=target_diff)

    existing_quiz = db.query(models.Quiz).filter(models.Quiz.lecture_id == lecture_id).first()
    if existing_quiz:
        existing_quiz.questions = quiz_json
    else:
        existing_quiz = models.Quiz(lecture_id=lecture_id, questions=quiz_json)
        db.add(existing_quiz)

    db.commit()
    db.refresh(existing_quiz)

    return {
        "message": f"Quiz paper dynamically adapted to '{target_diff}' difficulty",
        "difficulty": target_diff,
        "biometrics": bio_status,
        "quiz": existing_quiz
    }

from services.frame_buffer_grabber import frame_grabber

class FrameBufferStartRequest(BaseModel):
    video_path: Optional[str] = None

@app.get("/system/framebuffer")
def get_framebuffer_telemetry():
    """
    Returns real-time telemetry from the display output frame buffer grabber (Option #5):
    status, resolution, FPS, bus bandwidth (MB/s), latency (ms), and detected slide changes.
    """
    return frame_grabber.get_telemetry()

@app.post("/system/framebuffer/start")
def start_framebuffer_capture(request: Optional[FrameBufferStartRequest] = None):
    """
    Starts real-time monitoring of projector / smart whiteboard display output
    directly from hardware frame buffer registers.
    """
    path = request.video_path if request else None
    return frame_grabber.start_capture(video_path=path)

@app.post("/system/framebuffer/stop")
def stop_framebuffer_capture():
    """
    Stops frame buffer monitoring and returns capture summary.
    """
    return frame_grabber.stop_capture()

@app.get("/system/framebuffer/snapshots")
def get_framebuffer_snapshots():
    """
    Returns real-time keyframe snapshots captured from the hardware display buffer,
    including annotated bounding boxes, detected diagram/text regions, and OCR extractions.
    """
    return frame_grabber.get_snapshots()

@app.post("/system/framebuffer/next-slide")
def advance_framebuffer_slide():
    """
    Simulates a lecturer advancing the projector to the next diagram, formula, or whiteboard slide,
    forcing an immediate visual delta keyframe registration event.
    """
    return frame_grabber.force_next_slide()



