from typing import Literal, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db import get_db
from models import Assignment, Report, Submission
from services.ai_detect import detect_ai
from services.extract import extract_text_from_pdf, split_sentences
from services.plagiarism import analyze_plagiarism, load_reference_items
from services.report import build_report

router = APIRouter(prefix="/submissions", tags=["submissions"])


class ReviewIn(BaseModel):
    note: Optional[str] = None
    decision: Optional[Literal["accepted", "flagged"]] = None


@router.post("")
def create_submission(
    assignment_id: int = Form(...),
    student_name: str = Form(...),
    text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
):
    if not db.get(Assignment, assignment_id):
        raise HTTPException(404, "Assignment not found")

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

    sentences = split_sentences(raw)
    if not sentences:
        raise HTTPException(400, "Not enough text to analyze")

    # Class-wide comparison: same assignment ki baaki submissions
    peers = db.query(Submission).filter(Submission.assignment_id == assignment_id).all()
    peer_items = []
    for p in peers:
        for s in split_sentences(p.text):
            peer_items.append({"text": s, "source": f"Submission by {p.student_name}"})

    plag_flags = analyze_plagiarism(sentences, peer_items)
    ai_result = detect_ai(sentences)
    ref_count = len(load_reference_items()[0]) + len(peer_items)
    report = build_report(sentences, plag_flags, ai_result, ref_count)

    sub = Submission(
        assignment_id=assignment_id,
        student_name=student_name.strip(),
        text=raw,
        originality_score=report["originality_score"],
        ai_probability=report["ai_probability"],
        confidence=report["confidence"],
        status="analyzed",
    )
    db.add(sub)
    db.flush()
    db.add(Report(submission_id=sub.id, flagged=report))
    db.commit()

    return {"submission_id": sub.id, "student_name": sub.student_name, **report}


@router.get("")
def list_submissions(assignment_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.id.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "student_name": s.student_name,
            "originality_score": s.originality_score,
            "ai_probability": s.ai_probability,
            "confidence": s.confidence,
            "status": s.status,
            "decision": s.report.decision if s.report else None,
            "created_at": s.created_at,
        }
        for s in rows
    ]


@router.get("/{submission_id}/report")
def get_report(submission_id: int, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub or not sub.report:
        raise HTTPException(404, "Report not found")
    return {
        "submission_id": sub.id,
        "student_name": sub.student_name,
        "decision": sub.report.decision,
        "educator_note": sub.report.educator_note,
        **sub.report.flagged,
    }


@router.post("/{submission_id}/review")
def review_submission(submission_id: int, body: ReviewIn, db: Session = Depends(get_db)):
    sub = db.get(Submission, submission_id)
    if not sub or not sub.report:
        raise HTTPException(404, "Report not found")
    if body.note is not None:
        sub.report.educator_note = body.note
    if body.decision is not None:
        sub.report.decision = body.decision
    db.commit()
    return {
        "submission_id": sub.id,
        "decision": sub.report.decision,
        "educator_note": sub.report.educator_note,
    }