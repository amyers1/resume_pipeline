"""
Data models for resume pipeline.

Updated for Python 3.14 and PostgreSQL backend compatibility.
"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class Achievement(BaseModel):
    """Individual achievement with impact metrics."""

    description: str
    impact_metric: str | None = None
    domain_tags: list[str] = Field(default_factory=list)


class Role(BaseModel):
    """Work role with achievements."""

    title: str
    organization: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    seniority: str | None = None
    achievements: list[Achievement] = Field(default_factory=list)


class ProfileLocation(BaseModel):
    """Location information."""

    city: str | None = None
    region: str | None = None
    countryCode: str | None = None


class ProfileProfile(BaseModel):
    """Social media profile."""

    network: str | None = None
    url: str | None = None


class ProfileBasics(BaseModel):
    """Basic profile information."""

    name: str
    label: str | None = None
    email: str | None = None
    phone: str | None = None
    url: str | None = None
    summary: str | None = None
    location: ProfileLocation | None = None
    profiles: list[ProfileProfile] = Field(default_factory=list)


class ProfileExperienceHighlight(BaseModel):
    """Structured experience highlight."""

    description: str
    impact_metric: str | None = None
    domain_tags: list[str] = Field(default_factory=list)


class ProfileWork(BaseModel):
    """Work experience entry."""

    name: str
    position: str
    startDate: str | None = None
    endDate: str | None = None
    summary: str | None = None
    highlights: list[str] = Field(default_factory=list)
    # Support both structured achievements and legacy string highlights
    achievements: list[str | ProfileExperienceHighlight | dict[str, Any]] | None = None


class ProfileEducation(BaseModel):
    """Education entry."""

    institution: str
    area: str | None = None
    studyType: str | None = None
    startDate: str | None = None
    endDate: str | None = None
    location: str | None = None
    score: str | None = None
    courses: list[str] = Field(default_factory=list)


class ProfileAward(BaseModel):
    """Award or recognition."""

    title: str
    date: str | None = None
    awarder: str | None = None
    summary: str | None = None


class ProfileCertification(BaseModel):
    """Professional certification."""

    name: str
    date: str | None = None
    issuer: str | None = None
    url: str | None = None


class ProfileSkill(BaseModel):
    """Skill with proficiency level."""

    name: str
    level: str | None = None
    keywords: list[str] = Field(default_factory=list)


class ProfileProject(BaseModel):
    """Project entry."""

    name: str
    description: str | None = None
    highlights: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    startDate: str | None = None
    endDate: str | None = None
    url: str | None = None
    roles: list[str] = Field(default_factory=list)


class CareerProfile(BaseModel):
    """
    Complete career profile in JSON Resume format.

    This model is compatible with both:
    - Direct JSON Resume format files
    - PostgreSQL backend CareerProfile.to_full_json() output
    """

    basics: ProfileBasics
    work: list[ProfileWork] = Field(default_factory=list)
    education: list[ProfileEducation] = Field(default_factory=list)
    skills: list[ProfileSkill] = Field(default_factory=list)
    awards: list[ProfileAward] = Field(default_factory=list)
    certifications: list[ProfileCertification] = Field(default_factory=list)
    projects: list[ProfileProject] = Field(default_factory=list)
    languages: list[dict[str, str]] = Field(default_factory=list)

    # --- Convenience Properties for Template Access ---

    @property
    def full_name(self) -> str:
        """Get full name from basics."""
        return self.basics.name

    @property
    def contact_info(self) -> str:
        """Format contact information as single string."""
        parts = []
        if self.basics.email:
            parts.append(self.basics.email)
        if self.basics.phone:
            parts.append(self.basics.phone)
        if self.basics.location and self.basics.location.city:
            loc = self.basics.location
            city_region = f"{loc.city}, {loc.region}" if loc.region else loc.city
            parts.append(city_region)
        return " | ".join(parts)

    # --- Field Validators for Backward Compatibility ---

    @field_validator("awards", mode="before")
    @classmethod
    def validate_awards(cls, v: Any) -> list[dict[str, Any]]:
        """
        Handle legacy awards format where awards might be simple strings.
        Converts string awards to structured format.
        """
        if not isinstance(v, list):
            return []

        clean = []
        for item in v:
            if isinstance(item, str):
                # Legacy format: simple string
                clean.append({"title": item})
            elif isinstance(item, dict):
                # Already structured
                clean.append(item)
            else:
                # Unknown format, try to convert
                clean.append({"title": str(item)})
        return clean

    @field_validator("certifications", mode="before")
    @classmethod
    def validate_certs(cls, v: Any) -> list[dict[str, Any]]:
        """
        Handle legacy certifications format where certs might be simple strings.
        Converts string certifications to structured format.
        """
        if not isinstance(v, list):
            return []

        clean = []
        for item in v:
            if isinstance(item, str):
                # Legacy format: simple string
                clean.append({"name": item})
            elif isinstance(item, dict):
                # Already structured
                clean.append(item)
            else:
                # Unknown format, try to convert
                clean.append({"name": str(item)})
        return clean

    def to_prompt_string(self) -> str:
        """
        Flatten the structured profile for LLM context.

        Creates a readable text representation suitable for including
        in LLM prompts without overwhelming token count.
        """
        parts = []

        # Basic info
        parts.append(f"Name: {self.basics.name}")
        if self.basics.label:
            parts.append(f"Title: {self.basics.label}")
        if self.basics.summary:
            parts.append(f"Summary: {self.basics.summary}")

        # Work experience
        if self.work:
            parts.append("\nWork Experience:")
            for job in self.work:
                date_range = f"{job.startDate or ''} - {job.endDate or 'Present'}"
                parts.append(f"  - {job.position} at {job.name} ({date_range})")
                if job.highlights:
                    for highlight in job.highlights[:3]:  # Limit to top 3
                        parts.append(f"    • {highlight}")

        # Education
        if self.education:
            parts.append("\nEducation:")
            for edu in self.education:
                parts.append(
                    f"  - {edu.studyType or ''} {edu.area or ''} from {edu.institution}"
                )

        # Skills
        if self.skills:
            skill_names = [s.name for s in self.skills[:10]]  # Top 10 skills
            parts.append(f"\nKey Skills: {', '.join(skill_names)}")

        # Certifications
        if self.certifications:
            parts.append("\Certifications:")
            for cert in self.certifications[:5]:  # Limit to top 5
                date_str = f" ({cert.date})" if cert.date else ""
                issuer_str = f" - {cert.issuer}" if cert.issuer else ""
                parts.append(f"  - {cert.name}{issuer_str}{date_str}")

        # Awards
        if self.awards:
            parts.append("\nAwards:")
            for award in self.awards[:5]:  # Limit to top 5
                date_str = f" ({award.date})" if award.date else ""
                issuer_str = f" - {award.awarder}" if award.awarder else ""
                parts.append(f"  - {award.title}{issuer_str}{date_str}")

        return "\n".join(parts)


class JDRequirements(BaseModel):
    """Structured job description requirements."""

    role_title: str
    company: str
    location: str | None = None
    seniority_level: str | None = None
    domain_focus: list[str] = Field(default_factory=list)
    must_have_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    required_experience_years: int | None = None
    required_education: str | None = None
    key_responsibilities: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    """Single experience entry in formatted resume."""

    organization: str
    role_title: str
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)
    is_grouped: bool = False  # For "Other Relevant Experience" section


class EducationEntry(BaseModel):
    """Single education entry in formatted resume."""

    institution: str
    degree: str
    location: str | None = None
    graduation_date: str | None = None


class StructuredResume(BaseModel):
    """
    Final structured resume ready for template rendering.

    This is the output format used by templates (Jinja2, LaTeX).
    """

    full_name: str
    email: str
    phone: str
    location: str
    linkedin: str
    role_title: str | None = None
    professional_summary: list[str] = Field(default_factory=list)
    core_competencies: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[ProfileCertification] = Field(default_factory=list)
    awards: list[ProfileAward] = Field(default_factory=list)
    final_score: float | None = None


class CritiqueResult(BaseModel):
    """Resume critique evaluation results."""

    score: float = Field(..., ge=0.0, le=1.0)
    ats_ok: bool
    length_ok: bool
    jd_keyword_coverage: float = Field(..., ge=0.0, le=1.0)
    domain_match_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class CachedPipelineState(BaseModel):
    """
    Cached state to avoid redundant API calls.

    Stored in Redis with TTL. Keyed by hash of (job + career profile).
    """

    job_hash: str
    career_hash: str
    jd_requirements: JDRequirements
    matched_achievements: list[Achievement]
    draft_resume: str
    timestamp: str
