"""
Data models for resume pipeline.
"""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator


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


class ProfileLocation(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    countryCode: Optional[str] = None


class ProfileProfile(BaseModel):
    network: Optional[str] = None
    url: Optional[str] = None


class ProfileBasics(BaseModel):
    name: str
    label: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    url: Optional[str] = None
    summary: Optional[str] = None
    location: Optional[ProfileLocation] = None
    profiles: List[ProfileProfile] = []


class ProfileExperienceHighlight(BaseModel):
    description: str
    impact_metric: Optional[str] = None
    domain_tags: List[str] = []


class ProfileWork(BaseModel):
    name: str
    position: str
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: List[str] = []
    # Support the structured achievements as well
    achievements: Optional[
        List[Union[str, ProfileExperienceHighlight, Dict[str, Any]]]
    ] = None


class ProfileEducation(BaseModel):
    institution: str
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: List[str] = []


class ProfileAward(BaseModel):
    title: str
    date: Optional[str] = None
    awarder: Optional[str] = None
    summary: Optional[str] = None


class ProfileCertification(BaseModel):
    name: str
    date: Optional[str] = None
    issuer: Optional[str] = None
    url: Optional[str] = None


class ProfileSkill(BaseModel):
    name: str
    level: Optional[str] = None
    keywords: List[str] = []


class ProfileProject(BaseModel):
    name: str
    description: Optional[str] = None
    highlights: List[str] = []
    keywords: List[str] = []
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    url: Optional[str] = None
    roles: List[str] = []


# --- Main CareerProfile Model ---


class CareerProfile(BaseModel):
    basics: ProfileBasics
    work: List[ProfileWork] = []
    education: List[ProfileEducation] = []
    skills: List[ProfileSkill] = []

    # These match the DB's new output structure
    awards: List[ProfileAward] = []
    certifications: List[ProfileCertification] = []
    projects: List[ProfileProject] = []
    languages: List[Dict[str, str]] = []

    # --- Backward Compatibility / Convenience Properties ---
    # These allow the rest of the pipeline (like prompts) to access fields
    # cleanly without needing to rewrite every single Jinja2 template.

    @property
    def full_name(self) -> str:
        return self.basics.name

    @property
    def contact_info(self) -> str:
        parts = []
        if self.basics.email:
            parts.append(self.basics.email)
        if self.basics.phone:
            parts.append(self.basics.phone)
        if self.basics.location and self.basics.location.city:
            loc = self.basics.location
            parts.append(f"{loc.city}, {loc.region or ''}")
        return " | ".join(parts)

    @field_validator("awards", mode="before")
    @classmethod
    def validate_awards(cls, v):
        """Handle case where awards might be strings (legacy) vs objects (new)."""
        clean = []
        for item in v:
            if isinstance(item, str):
                clean.append({"title": item})
            else:
                clean.append(item)
        return clean

    @field_validator("certifications", mode="before")
    @classmethod
    def validate_certs(cls, v):
        """Handle case where certs might be strings (legacy) vs objects (new)."""
        clean = []
        for item in v:
            if isinstance(item, str):
                clean.append({"name": item})
            else:
                clean.append(item)
        return clean

    def to_prompt_string(self) -> str:
        """Helper to flatten the structured profile for LLM Context."""
        lines = []
        lines.append(f"Name: {self.basics.name}")
        lines.append(f"Summary: {self.basics.summary}")

        lines.append("\nEXPERIENCE:")
        for w in self.work:
            lines.append(f"- {w.position} at {w.name} ({w.startDate} - {w.endDate})")
            if w.summary:
                lines.append(f"  Summary: {w.summary}")

            # Handle structured achievements vs string highlights
            if w.achievements:
                for ach in w.achievements:
                    if isinstance(ach, dict) or hasattr(ach, "description"):
                        desc = (
                            ach.get("description")
                            if isinstance(ach, dict)
                            else ach.description
                        )
                        metric = (
                            ach.get("impact_metric")
                            if isinstance(ach, dict)
                            else ach.impact_metric
                        )
                        line = f"  * {desc}"
                        if metric:
                            line += f" [Impact: {metric}]"
                        lines.append(line)
                    else:
                        lines.append(f"  * {str(ach)}")
            elif w.highlights:
                for h in w.highlights:
                    lines.append(f"  * {h}")

        lines.append("\nEDUCATION:")
        for edu in self.education:
            lines.append(
                f"- {edu.studyType} in {edu.area} at {edu.institution} ({edu.endDate})"
            )

        lines.append("\nCERTIFICATIONS:")
        for c in self.certifications:
            lines.append(f"- {c.name}" + (f" ({c.date})" if c.date else ""))

        lines.append("\nAWARDS:")
        for a in self.awards:
            lines.append(f"- {a.title}")

        return "\n".join(lines)


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
