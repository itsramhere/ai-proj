import os
import matplotlib.pyplot as plt
import io
import base64
import json
import re
from openai import OpenAI
from services.llm import get_model_name, _extract_text_content

LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")

client = OpenAI(base_url=LMSTUDIO_BASE_URL, api_key=LMSTUDIO_API_KEY)

def extract_and_plot_trends(transcript: str) -> str:
    prompt = f"""
    Analyze the following transcript. If there are numeric trends or data points that can be plotted, extract them into a JSON format.
    Format: {{"has_data": true, "title": "Chart Title", "x_label": "X Axis", "y_label": "Y Axis", "x_data": ["A", "B"], "y_data": [1, 2]}}
    If no data, return {{"has_data": false}}. Return ONLY valid JSON.
    \n\n{transcript}
    """
    
    try:
        model = get_model_name()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You extract trend data into strictly valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        content = _extract_text_content(response.choices[0].message)
        json_match = re.search(r"\{[\s\S]*\}", content)
        if not json_match:
            return ""

        data = json.loads(json_match.group(0))
        if not data.get("has_data") or not data.get("x_data") or not data.get("y_data"):
            return ""
            
        plt.figure(figsize=(8, 5))
        plt.plot(data["x_data"], data["y_data"], marker="o")
        plt.title(data.get("title", "Trend"))
        plt.xlabel(data.get("x_label", "X"))
        plt.ylabel(data.get("y_label", "Y"))
        plt.grid(True)
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight")
        plt.close()
        buf.seek(0)
        
        img_str = base64.b64encode(buf.read()).decode("utf-8")
        return f"![Trend Chart](data:image/png;base64,{img_str})"
    except Exception as e:
        print(f"Notice: Trend plotting skipped ({e})", flush=True)
        return ""
