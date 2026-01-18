"""
Base template class for LaTeX generation.
"""

from abc import ABC, abstractmethod
import jinja2
from ..models import StructuredResume


class BaseTemplate(ABC):
    """Abstract base class for resume templates."""

    def __init__(self):
        self.env = self._create_jinja_env()
        self.env.filters["latex_escape"] = self.latex_escape

    def _create_jinja_env(self) -> jinja2.Environment:
        """Create Jinja2 environment with LaTeX delimiters."""
        return jinja2.Environment(
            block_start_string=r"\BLOCK{",
            block_end_string="}",
            variable_start_string=r"\VAR{",
            variable_end_string="}",
            comment_start_string=r"\#{",
            comment_end_string="}",
            trim_blocks=True,
            autoescape=False,
        )

    @staticmethod
    def latex_escape(s: str) -> str:
        """Escape LaTeX special characters."""
        mapping = {
            "&": r"\&",
            "%": r"\%",
            "$": r"\$",
            "#": r"\#",
            "_": r"\_",
            "{": r"\{",
            "}": r"\}",
            "~": r"\textasciitilde{}",
            "^": r"\^{}",
            "\\": r"\textbackslash{}",
        }
        return "".join(mapping.get(c, c) for c in str(s))

    @abstractmethod
    def get_template_string(self) -> str:
        """Return the Jinja2 template string."""
        pass

    def render(self, structured_resume: StructuredResume) -> str:
        """
        Render the template with resume data.

        Args:
            structured_resume: Structured resume data

        Returns:
            Rendered LaTeX document
        """
        template_str = self.get_template_string()
        template = self.env.from_string(template_str)
        return template.render(**structured_resume.model_dump())
