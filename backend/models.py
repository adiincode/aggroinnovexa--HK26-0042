from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.orm import mapped_column

from db import Base


class Assignment(Base):
    __tablename__ = "assignments"

    id = mapped_column(Integer, primary_key=True, index=True)
    title = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    submissions = relationship(
        "Submission", back_populates="assignment", cascade="all, delete-orphan"
    )


class Submission(Base):
    __tablename__ = "submissions"

    id = mapped_column(Integer, primary_key=True, index=True)
    assignment_id = mapped_column(
        Integer, ForeignKey("assignments.id"), nullable=False, index=True
    )
    student_name = mapped_column(String(255), nullable=False)
    text = mapped_column(Text, nullable=False, default="")
    originality_score = mapped_column(Float, nullable=True)
    ai_probability = mapped_column(Float, nullable=True)
    confidence = mapped_column(String(50), nullable=True)
    status = mapped_column(String(50), nullable=False, default="pending")
    created_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    assignment = relationship("Assignment", back_populates="submissions")
    report = relationship(
        "Report",
        back_populates="submission",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Report(Base):
    __tablename__ = "reports"

    id = mapped_column(Integer, primary_key=True, index=True)
    submission_id = mapped_column(
        Integer, ForeignKey("submissions.id"), nullable=False, unique=True
    )
    flagged = mapped_column(JSON, nullable=False)
    decision = mapped_column(String(20), nullable=True)
    educator_note = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    submission = relationship("Submission", back_populates="report")