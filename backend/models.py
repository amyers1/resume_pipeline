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
from sqlalchemy.dialects.postgresql import ARRAY
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

    # Basics
    name = Column(String, nullable=False)
    label = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    url = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    clearance = Column(String, nullable=True)
    summary = Column(Text, nullable=True)

    # Location
    city = Column(String, nullable=True)
    region = Column(String, nullable=True)
    country_code = Column(String, nullable=True)

    # Lists
    skills = Column(ARRAY(String), default=[])
    languages = Column(ARRAY(String), default=[])
    core_domains = Column(ARRAY(String), default=[])

    # Awards
    awards = Column(ARRAY(String), default=[])

    # Biography
    biography = Column(Text, nullable=True)

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

    certifications = relationship(
        "CareerCertification", back_populates="profile", cascade="all, delete-orphan"
    )

    def to_full_json(self) -> Dict[str, Any]:
        """Reconstructs standard JSON Resume format."""
        profiles = []
        if self.linkedin:
            profiles.append({"network": "LinkedIn", "url": self.linkedin})

        return {
            "basics": {
                "name": self.name,
                "label": self.label,
                "email": self.email,
                "phone": self.phone,
                "url": self.url,
                "linkedin": self.linkedin,
                "clearance": self.clearance,
                "summary": self.summary,
                "location": {
                    "city": self.city,
                    "region": self.region,
                    "countryCode": self.country_code,
                },
                "profiles": profiles,
            },
            "work": [item.to_json() for item in self.experience],
            "education": [item.to_json() for item in self.education],
            "projects": [item.to_json() for item in self.projects],
            "certifications": [item.to_json() for item in self.certifications],
            "awards": [{"title": a} for a in (self.awards or [])],
            "skills": [{"name": s} for s in (self.skills or [])],
            "core_domains": self.core_domains or [],
            "biography": self.biography,
        }


class CareerCertification(Base):
    __tablename__ = "career_certifications"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("career_profiles.id"), nullable=False)

    name = Column(String, nullable=False)
    organization = Column(String, nullable=True)
    date = Column(String, nullable=True)  # Year or ISO date

    profile = relationship("CareerProfile", back_populates="certifications")

    def to_json(self):
        return {"name": self.name, "issuer": self.organization, "date": self.date}


class CareerExperience(Base):
    __tablename__ = "career_experience"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("career_profiles.id"), nullable=False)

    company = Column(String, nullable=False)
    position = Column(String, nullable=False)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    is_current = Column(Boolean, default=False)
    location = Column(String, nullable=True)
    seniority = Column(String, nullable=True)
    summary = Column(Text, nullable=True)

    # NEW: Relationship to structured highlights (replaces old array)
    highlights = relationship(
        "CareerExperienceHighlight",
        back_populates="experience",
        cascade="all, delete-orphan",
    )

    profile = relationship("CareerProfile", back_populates="experience")

    def to_json(self):
        return {
            "name": self.company,
            "position": self.position,
            "startDate": self.start_date,
            "endDate": self.end_date,
            "location": self.location,
            "seniority": self.seniority,
            "summary": self.summary,
            "highlights": [
                h.description for h in self.highlights
            ],  # Flatten for standard JSON Resume
            "achievements": [
                h.to_json() for h in self.highlights
            ],  # Keep structure for our internal use
        }


class CareerExperienceHighlight(Base):
    __tablename__ = "career_experience_highlights"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    experience_id = Column(String, ForeignKey("career_experience.id"), nullable=False)

    description = Column(Text, nullable=False)
    impact_metric = Column(String, nullable=True)
    domain_tags = Column(ARRAY(String), default=[])
    skills = Column(ARRAY(String), default=[])

    experience = relationship("CareerExperience", back_populates="highlights")

    def to_json(self):
        return {
            "description": self.description,
            "impact_metric": self.impact_metric,
            "domain_tags": self.domain_tags or [],
            "skills": self.skills or [],
        }


class CareerEducation(Base):
    __tablename__ = "career_education"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    profile_id = Column(String, ForeignKey("career_profiles.id"), nullable=False)

    institution = Column(String, nullable=False)
    area = Column(String, nullable=True)
    study_type = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    location = Column(String, nullable=True)
    score = Column(String, nullable=True)
    courses = Column(ARRAY(String), default=[])

    profile = relationship("CareerProfile", back_populates="education")

    def to_json(self):
        return {
            "institution": self.institution,
            "area": self.area,
            "studyType": self.study_type,
            "endDate": self.end_date,
            "location": self.location,
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
            "keywords": self.keywords or [],
        }


# --- JOB MODEL (Unchanged) ---
class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), index=True)
    root_job_id = Column(String, index=True, nullable=True)
    status = Column(String, default="queued", index=True)

    # 1. DETAILS
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

    # URLs
    job_post_url = Column(String, nullable=True)
    apply_url = Column(String, nullable=True)
    posting_age = Column(String, nullable=True)

    # Clearance
    security_clearance_required = Column(String, nullable=True)
    security_clearance_preferred = Column(String, nullable=True)

    # Search Context
    search_keywords = Column(String, nullable=True)
    search_location = Column(String, nullable=True)
    search_radius = Column(Integer, nullable=True)

    # 2. BENEFITS
    benefits_listed = Column(ARRAY(String), default=[])
    benefits_text = Column(Text, nullable=True)
    benefits_eligibility = Column(String, nullable=True)
    benefits_relocation = Column(String, nullable=True)
    benefits_sign_on_bonus = Column(String, nullable=True)

    # 3. DESCRIPTION
    jd_headline = Column(String, nullable=True)
    jd_short_summary = Column(String, nullable=True)
    jd_full_text = Column(Text, nullable=True)
    jd_experience_min = Column(Integer, nullable=True)
    jd_education = Column(String, nullable=True)
    jd_must_have_skills = Column(ARRAY(String), default=[])
    jd_nice_to_have_skills = Column(ARRAY(String), default=[])

    # 4. CONFIG
    career_profile_json = Column(JSON)
    template = Column(String)
    output_backend = Column(String)
    priority = Column(Integer, default=5)
    advanced_settings = Column(JSON, default={})

    # Metrics
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    critique_json = Column(JSON, nullable=True)  # Full critique results

    output_files = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    user = relationship("User", back_populates="jobs")

    def to_dict(self):
        """Converts the Job object to a dictionary for SSE messages."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "root_job_id": self.root_job_id,
            "status": self.status,
            "company": self.company,
            "job_title": self.job_title,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "template": self.template,
            "output_backend": self.output_backend,
            "priority": self.priority,
            "final_score": self.final_score,
            "critique": self.critique_json,
        }

    def to_schema_json(self) -> Dict[str, Any]:
        return {
            "job_details": {
                "source": self.source,
                "platform": self.platform,
                "job_title": self.job_title,
                "company": self.company,
                "location": self.location,
                "pay_display": self.pay_display,
                "remote_type": self.remote_type,
                "job_post_url": self.job_post_url,
                "security_clearance_required": self.security_clearance_required,
            },
            "job_description": {
                "full_text": self.jd_full_text,
                "must_have_skills": self.jd_must_have_skills or [],
            },
        }


# ==========================
# PYDANTIC MODELS
# ==========================


class AdvancedSettings(BaseModel):
    base_model: Optional[str] = "gpt-4o"
    strong_model: Optional[str] = "gpt-4o"
    temperature: Optional[float] = 0.7
    max_critique_loops: Optional[int] = 1
    min_quality_score: Optional[float] = 8.0
    enable_cover_letter: bool = False


class JobHistoryItem(BaseModel):
    id: str
    created_at: datetime
    status: str
    template: Optional[str] = None

    class Config:
        from_attributes = True


class JobSubmitRequest(BaseModel):
    profile_id: Optional[str] = None
    job_data: Dict[str, Any]
    career_profile_data: Optional[Dict[str, Any]] = None
    template: str = "awesome-cv"
    output_backend: str = "weasyprint"
    priority: int = 5
    user_id: Optional[str] = None
    advanced_settings: Optional[AdvancedSettings] = None


class CritiqueResponse(BaseModel):
    """Critique results for API response."""

    score: Optional[float] = None
    ats_ok: Optional[bool] = None
    length_ok: Optional[bool] = None
    jd_keyword_coverage: Optional[float] = None
    domain_match_coverage: Optional[float] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    suggestions: List[str] = []


class JDRequirementsSummary(BaseModel):
    """Summary of JD requirements for display."""

    domain_focus: List[str] = []
    must_have_skills: List[str] = []
    nice_to_have_skills: List[str] = []


class JobResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    root_job_id: Optional[str] = None
    company: str
    job_title: str
    status: str
    created_at: datetime
    template: Optional[str] = None  # Added this line
    output_backend: Optional[str] = None  # Added this line
    job_description_json: Optional[Dict[str, Any]] = None
    final_score: Optional[float] = None
    critique: Optional[CritiqueResponse] = None
    jd_requirements: Optional[JDRequirementsSummary] = None
    output_files: Optional[Dict[str, str]] = None
    advanced_settings: Optional[Dict[str, Any]] = None
    history: List[JobHistoryItem] = []

    class Config:
        from_attributes = True


class ProfileBase(BaseModel):
    profile_json: Dict[str, Any]


class ProfileCreate(ProfileBase):
    pass


class ProfileResponse(ProfileBase):
    id: str
    name: str
    user_id: str
    created_at: datetime
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


class ResubmitOptions(BaseModel):
    template: Optional[str] = None
    output_backend: Optional[str] = None
    priority: Optional[int] = None
    advanced_settings: Optional[Dict[str, Any]] = None
