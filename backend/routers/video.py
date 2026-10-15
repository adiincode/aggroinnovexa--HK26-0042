from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services import llm
from services.youtube import get_transcript

router = APIRouter(prefix="/video", tags=["student tools"])


class VideoIn(BaseModel):
    url: str
    num_questions: int = 5


@router.post("/process")
def process_video(body: VideoIn):
    try:
        transcript = get_transcript(body.url)
    except Exception as e:
        raise HTTPException(400, f"Could not get transcript: {e}")
    try:
        result = llm.summarize_and_quiz(transcript, body.num_questions)
    except Exception as e:
        raise HTTPException(502, f"LLM error: {e}")
    result["transcript_preview"] = transcript[:500]
    return result