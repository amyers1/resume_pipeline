"""
LaTeX resume generation with template support.
"""

import jinja2
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..models import CareerProfile, EducationEntry, StructuredResume
from ..templates import AwesomeCVTemplate, ModernDeedyTemplate


class LaTeXGenerator:
    """Generates LaTeX resumes from structured data."""

    def __init__(self, template_name: str):
        self.template_name = template_name.lower()
        self.template = self._load_template()

    def _load_template(self):
        """Load the specified template."""
        if self.template_name == "modern-deedy":
            return ModernDeedyTemplate()
        elif self.template_name == "awesome-cv":
            return AwesomeCVTemplate()
        else:
            raise ValueError(
                f"Unknown template: {self.template_name}. "
                "Use 'modern-deedy' or 'awesome-cv'"
            )

    def generate(self, structured_resume: StructuredResume) -> str:
        """
        Generate LaTeX from structured resume.

        Args:
            structured_resume: Structured resume data

        Returns:
            LaTeX document string
        """
        return self.template.render(structured_resume)


class StructuredResumeParser:
    """Parses markdown resumes to structured format."""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._setup_prompt()

    def _setup_prompt(self):
        """Initialize parsing prompt."""
        self.parser_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You convert markdown resumes to structured JSON. "
                    "Extract: full_name, email, phone, location, linkedin, role_title, "
                    "professional_summary (list of strings), core_competencies (list of strings), "
                    "experience (list of entries with: organization, role_title, location, start_date, end_date (dates in 'Mmm YYYY' format), bullets (list of strings), is_grouped (bool) = false). "
                    "For experience entries under 'Other Relevant Experience' heading, set is_grouped=true. "
                    "Education, certifications, and awards will be populated from the career profile, so leave them as empty lists. "
                    "Preserve all content accurately. Return StructuredResume JSON only.",
                ),
                (
                    "user",
                    "Markdown resume:\n{resume_md}\n\nConvert to StructuredResume JSON.",
                ),
            ]
        )

    def parse(self, resume_md: str, career_profile: CareerProfile) -> StructuredResume:
        """
        Parse markdown resume to structured format.

        Args:
            resume_md: Resume in markdown format
            career_profile: The user's career profile for sourcing contact info.

        Returns:
            Structured resume object
        """
        chain = self.parser_prompt | self.llm.with_structured_output(StructuredResume)
        structured_resume = chain.invoke({"resume_md": resume_md})

        # Overwrite contact info with the authoritative source from the profile
        if career_profile and career_profile.basics:
            basics = career_profile.basics
            structured_resume.full_name = basics.name
            structured_resume.email = basics.email
            structured_resume.phone = basics.phone
            structured_resume.linkedin = basics.url
            if basics.location:
                structured_resume.location = (
                    f"{basics.location.city}, {basics.location.region}"
                )

        # Populate education, certifications, and awards from career profile
        if career_profile:
            # Convert education entries to EducationEntry format
            structured_resume.education = [
                EducationEntry(
                    institution=edu.institution,
                    degree=f"{edu.studyType} {edu.area}".strip()
                    if edu.studyType or edu.area
                    else "",
                    location=edu.location,
                    graduation_date=edu.endDate,
                )
                for edu in career_profile.education
            ]

            # Certifications and awards are already in the correct format
            structured_resume.certifications = career_profile.certifications
            structured_resume.awards = career_profile.awards

        return structured_resume
