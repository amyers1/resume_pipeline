from datetime import datetime
from typing import Optional, Dict, List, Any
import uuid

from sqlalchemy import Column, String, Integer, DateTime, JSON, Float, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

from database import Base

# ==========================
# SQLALCHEMY MODELS (DB)
# ==========================

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    profiles = relationship("CareerProfile", back_populates="user", cascade="all, delete-orphan")

class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, default="Default Profile") # e.g., "Tech Lead", "Individual Contributor"

    # The actual resume data (summary, experience, education, etc.)
    profile_json = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="profiles")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True) # Nullable for now to support legacy/migration
    company = Column(String, index=True)
    job_title = Column(String)
    status = Column(String, default="queued", index=True)

    # Inputs
    job_description_json = Column(JSON)
    career_profile_json = Column(JSON) # Snapshot of the profile used for this specific run

    # Configuration
    template = Column(String)
    output_backend = Column(String)
    priority = Column(Integer, default=5)

    # Metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    # Outputs
    output_files = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")

# ==========================
# PYDANTIC MODELS (API)
# ==========================

# --- User Models ---
class UserBase(BaseModel):
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    id: str
    created_at: datetime
    class Config:
        from_attributes = True

# --- Profile Models ---
class ProfileBase(BaseModel):
    name: str
    profile_json: Dict[str, Any]

class ProfileCreate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: str
    user_id: str
    created_at: datetime
    class Config:
        from_attributes = True

# --- Job Models (Updated) ---
class JobSubmitRequest(BaseModel):
    # Optional: If provided, we look up this profile from DB.
    # If null, we expect 'career_profile_data' to be provided manually.
    profile_id: Optional[str] = None

    job_data: Dict[str, Any]
    career_profile_data: Optional[Dict[str, Any]] = None # Fallback if no profile_id

    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = 5
    user_id: Optional[str] = None # In a real app, this comes from Auth token

class JobResponse(BaseModel):
    id: str
    company: str
    job_title: str
    status: str
    created_at: datetime
    final_score: Optional[float] = None
    output_files: Optional[Dict[str, str]] = None
    user_id: Optional[str] = None

    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    size: int
