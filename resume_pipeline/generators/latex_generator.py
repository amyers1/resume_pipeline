"""
LaTeX resume generation with template support.
"""

import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..models import StructuredResume
from ..templates import ModernDeedyTemplate, AwesomeCVTemplate


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
        self.parser_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You convert markdown resumes to structured JSON. "
             "Extract: full_name, email, phone, location, linkedin, role_title, "
             "professional_summary (list), core_competencies (list), "
             "experience (list of entries with title, organization, location, dates, bullets, is_grouped flag), "
             "education (list), certifications (list), awards (list). "
             "For experience entries under 'Other Relevant Experience' heading, set is_grouped=true. "
             "Preserve all content accurately. Return StructuredResume JSON only."),
            ("user", "Markdown resume:\n{resume_md}\n\nConvert to StructuredResume JSON.")
        ])

    def parse(self, resume_md: str) -> StructuredResume:
        """
        Parse markdown resume to structured format.

        Args:
            resume_md: Resume in markdown format

        Returns:
            Structured resume object
        """
        chain = self.parser_prompt | self.llm.with_structured_output(StructuredResume)
        return chain.invoke({"resume_md": resume_md})
