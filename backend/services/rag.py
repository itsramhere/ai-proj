import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from services.llm import get_model_name, _extract_text_content

LMSTUDIO_BASE_URL = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_API_KEY = os.getenv("LMSTUDIO_API_KEY", "lm-studio")

client = OpenAI(base_url=LMSTUDIO_BASE_URL, api_key=LMSTUDIO_API_KEY)

_embedder = None
dimension = 384 # Output dimension of all-MiniLM-L6-v2

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder

class RAGStore:
    def __init__(self):
        self.index = faiss.IndexFlatL2(dimension)
        self.chunks = []

    def add_document(self, text: str, chunk_size: int = 500):
        embedder = get_embedder()
        words = text.split()
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            if chunk:
                self.chunks.append(chunk)
        
        if self.chunks:
            embeddings = embedder.encode(self.chunks)
            self.index.add(np.array(embeddings).astype("float32"))

    def query(self, question: str, top_k: int = 3) -> str:
        if not self.chunks:
            return "No context available."
            
        embedder = get_embedder()
        question_embedding = embedder.encode([question])
        distances, indices = self.index.search(np.array(question_embedding).astype("float32"), top_k)
        
        context = ""
        for idx in indices[0]:
            if idx < len(self.chunks):
                context += self.chunks[idx] + "\n\n"
                
        prompt = f"Answer the user question based on the following context:\n\n{context}\n\nQuestion: {question}\nAnswer:"
        
        model = get_model_name()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You answer questions accurately based only on the provided context."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        return _extract_text_content(response.choices[0].message)
