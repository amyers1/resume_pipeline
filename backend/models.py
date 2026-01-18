import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Base
from pydantic import BaseModel, Field
from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

# ==========================
# SQLALCHEMY MODELS (DB)
# ==========================


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)  # Future proofing
    company = Column(String, index=True)
    job_title = Column(String)
    status = Column(
        String, default="queued", index=True
    )  # queued, processing, completed, failed

    # Inputs (Stored as JSONB in Postgres)
    job_description_json = Column(JSON)
    career_profile_json = Column(JSON)

    # Configuration
    template = Column(String)
    output_backend = Column(String)
    priority = Column(Integer, default=5)

    # Metrics & Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Outputs
    output_files = Column(JSON, nullable=True)  # {"pdf": "path/to/s3", "tex": "..."}
    error_message = Column(Text, nullable=True)


# ==========================
# PYDANTIC MODELS (API)
# ==========================


class JobSubmitRequest(BaseModel):
    job_data: Dict[str, Any]
    career_profile_data: Dict[str, Any]  # Accepting JSON directly now
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = 5
    enable_uploads: bool = True


class JobResponse(BaseModel):
    id: str
    company: str
    job_title: str
    status: str
    created_at: datetime
    final_score: Optional[float] = None
    output_files: Optional[Dict[str, str]] = None

    class Config:
        from_attributes = True  # updated for Pydantic v2 (was orm_mode)


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    size: int
