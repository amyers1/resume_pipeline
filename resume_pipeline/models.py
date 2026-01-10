"""
Data models for resume pipeline.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class Achievement(BaseModel):
    description: str
    impact_metric: Optional[str] = None
    domain_tags: List[str] = Field(default_factory=list)


class Role(BaseModel):
    title: str
    organization: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    seniority: Optional[str] = None
    achievements: List[Achievement] = Field(default_factory=list)


class CareerProfile(BaseModel):
    full_name: str
    clearance: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    location: Optional[str] = None
    core_domains: List[str] = Field(default_factory=list)
    roles: List[Role] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)


class JDRequirements(BaseModel):
    role_title: str
    seniority: str
    location: Optional[str] = None
    must_have_skills: List[str] = Field(default_factory=list)
    nice_to_have_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    clearance_or_eligibility: Optional[str] = None
    domain_focus: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)


class RankedAchievement(BaseModel):
    index: int
    reason: str


class RankedAchievementsResponse(BaseModel):
    items: List[RankedAchievement]


class ExperienceEntry(BaseModel):
    title: str
    organization: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)
    is_grouped: bool = False  # For "Other Relevant Experience"


class EducationEntry(BaseModel):
    institution: str
    degree: str
    location: Optional[str] = None
    graduation_date: Optional[str] = None


class StructuredResume(BaseModel):
    full_name: str
    email: str
    phone: str
    location: str
    linkedin: str
    role_title: Optional[str] = None
    professional_summary: List[str] = Field(default_factory=list)
    core_competencies: List[str] = Field(default_factory=list)
    experience: List[ExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)


class CritiqueResult(BaseModel):
    score: float = Field(..., ge=0.0, le=1.0)
    ats_ok: bool
    length_ok: bool
    jd_keyword_coverage: float = Field(..., ge=0.0, le=1.0)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


class CachedPipelineState(BaseModel):
    """Cached state to avoid redundant API calls."""
    job_hash: str
    career_hash: str
    jd_requirements: JDRequirements
    matched_achievements: List[Achievement]
    draft_resume: str
    timestamp: str
