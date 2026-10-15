from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from services import llm
from services.extract import clean_text, extract_text_from_pdf

router = APIRouter(prefix="/text", tags=["student tools"])


@router.post("/process")
def process_text(
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    num_questions: int = Form(5),
):
    raw = text or ""
    if file is not None and file.filename:
        data = file.file.read()
        name = file.filename.lower()
        if name.endswith(".pdf"):
            raw = extract_text_from_pdf(data)
        elif name.endswith(".txt"):
            raw = data.decode("utf-8", errors="ignore")
        else:
            raise HTTPException(400, "Only .pdf and .txt files are supported")

    raw = clean_text(raw)
    if len(raw.split()) < 20:
        raise HTTPException(400, "Please provide at least 20 words")

    try:
        return llm.summarize_and_quiz(raw, num_questions)
    except Exception as e:
        raise HTTPException(502, f"LLM error: {e}")