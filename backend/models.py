import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from database import Base
from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY  # Postgres specific array type
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

# ==========================
# SQLALCHEMY MODELS
# ==========================


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    profiles = relationship(
        "CareerProfile", back_populates="user", cascade="all, delete-orphan"
    )


class CareerProfile(Base):
    __tablename__ = "career_profiles"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # --- 1. BASICS ---
    name = Column(String, nullable=False)  # Full Name
    label = Column(String, nullable=True)  # e.g. "Senior Software Engineer"
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    url = Column(String, nullable=True)  # Website

    # Socials
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)

    # Location
    city = Column(String, nullable=True)
    region = Column(String, nullable=True)  # State
    country_code = Column(String, nullable=True)

    # Content
    summary = Column(Text, nullable=True)
    skills = Column(ARRAY(String), default=[])
    languages = Column(ARRAY(String), default=[])

    # Relationships
    user = relationship("User", back_populates="profiles")
    experience = relationship(
        "CareerExperience", back_populates="profile", cascade="all, delete-orphan"
    )
    education = relationship(
        "CareerEducation", back_populates="profile", cascade="all, delete-orphan"
    )
    projects = relationship(
        "CareerProject", back_populates="profile", cascade="all, delete-orphan"
    )

    def to_full_json(self) -> Dict[str, Any]:
        """Reconstructs standard JSON Resume format."""
        return {
            "basics": {
                "name": self.name,
                "label": self.label,
                "email": self.email,
                "phone": self.phone,
                "url": self.url,
                "summary": self.summary,
                "location": {
                    "city": self.city,
                    "region": self.region,
                    "countryCode": self.country_code,
                },
                "profiles": [
                    {"network": "LinkedIn", "url": self.linkedin_url},
                    {"network": "GitHub", "url": self.github_url},
                ],
            },
            "work": [item.to_json() for item in self.experience],
            "education": [item.to_json() for item in self.education],
            "projects": [item.to_json() for item in self.projects],
            "skills": [{"name": s} for s in (self.skills or [])],
            "languages": [{"language": l} for l in (self.languages or [])],
        }


class CareerExperience(Base):
    __tablename__ = "career_experience"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("career_profiles.id"), nullable=False)

    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    start_date = Column(String, nullable=True)  # ISO Date or "2020-01"
    end_date = Column(String, nullable=True)
    is_current = Column(Boolean, default=False)
    summary = Column(Text, nullable=True)
    highlights = Column(ARRAY(String), default=[])

    profile = relationship("CareerProfile", back_populates="experience")

    def to_json(self):
        return {
            "name": self.company,
            "position": self.position,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "summary": self.summary,
            "highlights": self.highlights or [],
        }


class CareerEducation(Base):
    __tablename__ = "career_education"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("career_profiles.id"), nullable=False)

    institution = Column(String, nullable=False)
    area = Column(String, nullable=True)  # Major
    study_type = Column(String, nullable=True)  # Degree type
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    score = Column(String, nullable=True)  # GPA
    courses = Column(ARRAY(String), default=[])

    profile = relationship("CareerProfile", back_populates="education")

    def to_json(self):
        return {
            "institution": self.institution,
            "area": self.area,
            "studyType": self.study_type,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "score": self.score,
            "courses": self.courses or [],
        }


class CareerProject(Base):
    __tablename__ = "career_projects"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("career_profiles.id"), nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String, nullable=True)
    keywords = Column(ARRAY(String), default=[])
    roles = Column(ARRAY(String), default=[])
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)

    profile = relationship("CareerProfile", back_populates="projects")

    def to_json(self):
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "keywords": self.keywords or [],
            "roles": self.roles or [],
            "startDate": self.start_date,
            "endDate": self.end_date,
        }


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="queued", index=True)

    # --- 1. JOB DETAILS ---
    company = Column(String, index=True)
    job_title = Column(String, index=True)
    source = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    company_rating = Column(String, nullable=True)
    location = Column(String, nullable=True)
    location_detail = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)

    # Pay
    pay_currency = Column(String, default="USD")
    pay_min_annual = Column(Integer, nullable=True)
    pay_max_annual = Column(Integer, nullable=True)
    pay_rate_type = Column(String, nullable=True)
    pay_display = Column(String, nullable=True)

    # Work Model
    remote_type = Column(String, nullable=True)
    work_model = Column(String, nullable=True)
    work_model_notes = Column(String, nullable=True)

    # URLs & Meta
    job_post_url = Column(String, nullable=True)
    apply_url = Column(String, nullable=True)
    posting_age = Column(String, nullable=True)

    # Clearance
    security_clearance_required = Column(String, nullable=True)
    security_clearance_preferred = Column(String, nullable=True)

    # Search Context (from job_board_list_context)
    search_keywords = Column(String, nullable=True)
    search_location = Column(String, nullable=True)
    search_radius = Column(Integer, nullable=True)

    # --- 2. BENEFITS ---
    # Using PostgreSQL ARRAY for lists
    benefits_listed = Column(ARRAY(String), default=[])
    benefits_text = Column(Text, nullable=True)
    benefits_eligibility = Column(String, nullable=True)
    benefits_relocation = Column(String, nullable=True)
    benefits_sign_on_bonus = Column(String, nullable=True)

    # --- 3. JOB DESCRIPTION ---
    jd_headline = Column(String, nullable=True)
    jd_short_summary = Column(String, nullable=True)
    jd_full_text = Column(Text, nullable=True)  # The raw text
    jd_experience_min = Column(Integer, nullable=True)
    jd_education = Column(String, nullable=True)

    # Skills
    jd_must_have_skills = Column(ARRAY(String), default=[])
    jd_nice_to_have_skills = Column(ARRAY(String), default=[])

    # --- CONFIGURATION & METRICS ---
    career_profile_json = Column(JSON)  # We still keep this as a snapshot
    template = Column(String)
    output_backend = Column(String)
    priority = Column(Integer, default=5)
    advanced_settings = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)

    output_files = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="jobs")

    def to_schema_json(self) -> Dict[str, Any]:
        """Reconstructs the original schema.json structure from DB columns."""
        return {
            "job_details": {
                "source": self.source,
                "platform": self.platform,
                "job_title": self.job_title,
                "company": self.company,
                "company_rating": self.company_rating,
                "location": self.location,
                "location_detail": self.location_detail,
                "employment_type": self.employment_type,
                "pay_currency": self.pay_currency,
                "pay_min_annual": self.pay_min_annual,
                "pay_max_annual": self.pay_max_annual,
                "pay_rate_type": self.pay_rate_type,
                "pay_display": self.pay_display,
                "remote_type": self.remote_type,
                "job_post_url": self.job_post_url,
                "apply_url": self.apply_url,
                "security_clearance_required": self.security_clearance_required,
                "security_clearance_preferred": self.security_clearance_preferred,
                "work_model": self.work_model,
                "work_model_notes": self.work_model_notes,
                "posting_age": self.posting_age,
                "job_board_list_context": {
                    "search_keywords": self.search_keywords,
                    "search_location": self.search_location,
                    "search_radius_miles": self.search_radius,
                },
            },
            "benefits": {
                "listed_benefits": self.benefits_listed or [],
                "benefits_text": self.benefits_text,
                "eligibility_notes": self.benefits_eligibility,
                "relocation": self.benefits_relocation,
                "sign_on_bonus": self.benefits_sign_on_bonus,
            },
            "job_description": {
                "headline": self.jd_headline,
                "short_summary": self.jd_short_summary,
                "full_text": self.jd_full_text,
                "required_experience_years_min": self.jd_experience_min,
                "required_education": self.jd_education,
                "must_have_skills": self.jd_must_have_skills or [],
                "nice_to_have_skills": self.jd_nice_to_have_skills or [],
            },
        }


# ==========================
# PYDANTIC MODELS (API)
# ==========================


class AdvancedSettings(BaseModel):
    base_model: Optional[str] = "gpt-4o"
    strong_model: Optional[str] = "gpt-4o"
    temperature: Optional[float] = 0.7
    max_critique_loops: Optional[int] = 1
    min_quality_score: Optional[float] = 8.0
    enable_cover_letter: bool = False


# Job Models
class JobSubmitRequest(BaseModel):
    profile_id: Optional[str] = None
    job_data: Dict[str, Any]
    career_profile_data: Optional[Dict[str, Any]] = None
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = 5
    user_id: Optional[str] = None
    advanced_settings: Optional[AdvancedSettings] = None


class JobResponse(BaseModel):
    id: str
    company: str
    job_title: str
    status: str
    created_at: datetime
    # We populate these from the reconstructor
    job_description_json: Optional[Dict[str, Any]] = None
    final_score: Optional[float] = None
    output_files: Optional[Dict[str, str]] = None
    advanced_settings: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Profile Models
class ProfileBase(BaseModel):
    # We accept a loose dictionary for creation to handle the JSON Resume format
    profile_json: Dict[str, Any] | None


class ProfileCreate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: str
    name: str
    user_id: str
    created_at: datetime
    # We populate this from .to_full_json()
    profile_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


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


class JobListResponse(BaseModel):
    items: List[JobResponse]
    total: int
    page: int
    size: int
