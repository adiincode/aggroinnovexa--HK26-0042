import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
MAX_CHARS = 12000

_client = None


def _get_client():
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key or key == "abhi_khali":
            raise RuntimeError("GROQ_API_KEY is not set in .env")
        _client = Groq(api_key=key)
    return _client


def summarize_and_quiz(text: str, num_questions: int = 5) -> dict:
    text = text[:MAX_CHARS]
    num_questions = max(1, min(num_questions, 10))
    prompt = (
        f"Read the text below. Return ONLY a JSON object with this exact shape:\n"
        f'{{"summary": "5-7 sentence summary", "questions": [{{"question": "...", '
        f'"options": ["A", "B", "C", "D"], "answer_index": 0, "explanation": "..."}}]}}\n'
        f"Create exactly {num_questions} multiple-choice questions with 4 options each.\n\n"
        f"TEXT:\n{text}"
    )
    resp = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a study assistant. Reply with valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def explain_code(code: str) -> str:
    resp = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You explain Python code to beginners in simple language."},
            {"role": "user", "content": f"Explain what this code does in 3-5 short sentences:\n\n{code[:4000]}"},
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()