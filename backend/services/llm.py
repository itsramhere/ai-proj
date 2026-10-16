import os
import json
import re
from openai import OpenAI

LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")

client = OpenAI(base_url=LMSTUDIO_BASE_URL, api_key=LMSTUDIO_API_KEY)

from services.thermal_agent import thermal_agent
from services.cleaner import clean_markdown_notes, sanitize_mermaid

def get_model_name() -> str:
    """
    Dynamically governs model selection via Reinforcement Learning agent based on physical hardware temperature.
    """
    decision = thermal_agent.select_model()
    model = decision["selected_model"]
    temp = decision["telemetry"]["primary_temp_c"]
    risk = decision["telemetry"]["throttling_risk"]
    print(f"[Thermal RL Governor] Hardware Temp: {temp}°C | Status: {risk} | Dispatched: {model} ({decision['model_tier']})", flush=True)
    return model

def _extract_text_content(message) -> str:
    """
    Extracts text from an OpenAI completion message, handling models that output reasoning_content.
    """
    content = getattr(message, "content", "") or ""
    if not content.strip():
        # Fallback to reasoning_content if model put text there
        content = getattr(message, "reasoning_content", "") or ""
    return content.strip()

def generate_notes(transcript: str) -> str:
    prompt = (
        "You are an expert academic tutor and note-taker. Summarize the following lecture transcript into "
        "comprehensive, well-structured study notes in Markdown format. Use clear headings, bullet points, "
        "bold key terms, and markdown tables where appropriate.\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Structured Markdown Notes:"
    )
    
    model = get_model_name()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that generates high-quality study notes."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    raw_notes = _extract_text_content(response.choices[0].message)
    return clean_markdown_notes(raw_notes)

def generate_diagrams(transcript: str) -> str:
    prompt = (
        "Analyze the following lecture transcript. If there are processes, sequential workflows, architectures, "
        "or hierarchies described, generate a valid Mermaid.js flowchart (starting with graph TD or flowchart TD). "
        "Output ONLY the raw Mermaid diagram syntax. Do NOT wrap it in backticks or markdown formatting. "
        "If no suitable process or hierarchy exists, respond with nothing.\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Mermaid Diagram:"
    )
    
    model = get_model_name()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You generate valid Mermaid.js diagram definitions only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )
    
    raw_content = _extract_text_content(response.choices[0].message)
    return sanitize_mermaid(raw_content)

def generate_quiz(transcript: str, difficulty: str = "medium") -> str:
    difficulty_instructions = {
        "easy": (
            "Target Difficulty: BEGINNER / FOUNDATIONAL (High Student Stress Mitigation). "
            "Focus on direct recall, basic definitions, clear distinguishing facts, and encouraging questions."
        ),
        "medium": (
            "Target Difficulty: INTERMEDIATE (Balanced Cognitive Load). "
            "Focus on understanding core mechanics, comparisons, and typical use cases."
        ),
        "hard": (
            "Target Difficulty: ADVANCED / CHALLENGING (Optimal Student Focus). "
            "Focus on deep analytical reasoning, edge cases, trade-offs, and critical problem solving."
        )
    }
    diff_note = difficulty_instructions.get(difficulty.lower(), difficulty_instructions["medium"])

    prompt = (
        f"Based on the following lecture transcript, generate a 5-10 question practice quiz testing key concepts.\n"
        f"ADAPTIVE DIFFICULTY DIRECTIVE: {diff_note}\n\n"
        "Return strictly valid JSON matching this exact structure:\n"
        "{\n"
        '  "difficulty": "' + difficulty + '",\n'
        '  "questions": [\n'
        "    {\n"
        '      "id": 1,\n'
        '      "difficulty": "' + difficulty + '",\n'
        '      "question": "Question text here?",\n'
        '      "options": ["Option A", "Option B", "Option C", "Option D"],\n'
        '      "correct_answer": "Option A",\n'
        '      "explanation": "Detailed explanation of why this is correct."\n'
        "    }\n"
        "  ]\n"
        "}\n"
        "Do NOT include any commentary outside the JSON.\n\n"
        f"Transcript:\n{transcript}"
    )
    
    model = get_model_name()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a quiz generator that outputs strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            response_format={"type": "json_object"}
        )
        content = _extract_text_content(response.choices[0].message)
    except Exception:
        # Fallback without json_object constraint if model doesn't support response_format
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a quiz generator that outputs strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        content = _extract_text_content(response.choices[0].message)

    # Clean markdown fences if model wrapped the JSON
    json_match = re.search(r"\{[\s\S]*\}", content)
    if json_match:
        content = json_match.group(0)

    return content
