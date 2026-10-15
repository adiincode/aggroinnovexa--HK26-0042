from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models import Assignment, Submission

router = APIRouter(prefix="/assignments", tags=["assignments"])


class AssignmentIn(BaseModel):
    title: str


@router.post("")
def create_assignment(body: AssignmentIn, db: Session = Depends(get_db)):
    title = body.title.strip()
    if not title:
        raise HTTPException(400, "Title is required")
    a = Assignment(title=title)
    db.add(a)
    db.commit()
    db.refresh(a)
    return {"id": a.id, "title": a.title, "created_at": a.created_at}


@router.get("")
def list_assignments(db: Session = Depends(get_db)):
    rows = db.query(Assignment).order_by(Assignment.id.desc()).all()
    return [{"id": a.id, "title": a.title, "created_at": a.created_at} for a in rows]


@router.get("/{assignment_id}/stats")
def assignment_stats(assignment_id: int, db: Session = Depends(get_db)):
    a = db.get(Assignment, assignment_id)
    if not a:
        raise HTTPException(404, "Assignment not found")

    subs = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    analyzed = [s for s in subs if s.status == "analyzed"]

    def avg(values, digits=1):
        return round(sum(values) / len(values), digits) if values else None

    high_risk = [
        s for s in analyzed
        if (s.originality_score is not None and s.originality_score < 50)
        or (s.ai_probability is not None and s.ai_probability >= 0.7)
    ]

    decisions = {"accepted": 0, "flagged": 0, "pending": 0}
    for s in analyzed:
        d = s.report.decision if s.report and s.report.decision else "pending"
        decisions[d] = decisions.get(d, 0) + 1

    return {
        "assignment_id": a.id,
        "title": a.title,
        "total_submissions": len(subs),
        "analyzed": len(analyzed),
        "avg_originality": avg([s.originality_score for s in analyzed if s.originality_score is not None]),
        "avg_ai_probability": avg([s.ai_probability for s in analyzed if s.ai_probability is not None], 2),
        "high_risk_count": len(high_risk),
        "decisions": decisions,
    }