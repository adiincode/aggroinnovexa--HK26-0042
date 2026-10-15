from fastapi import APIRouter
from pydantic import BaseModel

from services import llm
from services.tracer import trace_code

router = APIRouter(prefix="/code", tags=["student tools"])


class CodeIn(BaseModel):
    code: str
    explain: bool = True


@router.post("/visualize")
def visualize(body: CodeIn):
    result = trace_code(body.code)
    result["explanation"] = None
    if body.explain:
        try:
            result["explanation"] = llm.explain_code(body.code)
        except Exception:
            pass  # Groq key na ho to bhi trace chalega
    return result