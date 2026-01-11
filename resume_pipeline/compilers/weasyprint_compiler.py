"""
WeasyPrint compilation utilities.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import CSS, HTML  # type: ignore


class WeasyPrintCompiler:
    """Compiles HTML+CSS resumes to PDF using WeasyPrint."""

    def __init__(
        self,
        template_dir: Optional[Path] = None,
        css_file: Optional[str] = None,  # Made optional
    ):
        """
        Initialize WeasyPrint compiler.

        Args:
            template_dir: Directory containing HTML/Jinja2 templates and CSS
            css_file: Name of the CSS file in template_dir (if None, reads from env)
        """
        self.template_dir = template_dir or Path("resume_pipeline/templates")
        self._default_css_file = css_file or "resume.css"  # Store default fallback

        # Optional: sanity check for WeasyPrint import (installed via pip)
        weasyprint_path = shutil.which("weasyprint")
        if not weasyprint_path:
            print(
                "  ⚠ WeasyPrint CLI not found (Python API will still work if package is installed)"
            )

        # Prepare Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def _get_css_file(self) -> str:
        """
        Get the CSS file path, reading from environment if available.

        This ensures that changes to .env are picked up on each compile,
        without needing to restart the container or rebuild.

        Returns:
            CSS filename to use
        """
        # Try to read from environment variable first
        env_css = os.getenv("WEASYPRINT_CSS_FILE")

        if env_css:
            print(f"  Using CSS from environment: {env_css}")
            return env_css

        # Fall back to default
        return self._default_css_file

    def compile(
        self,
        output_pdf: Path,
        template_name: str,
        context: Dict[str, Any],
        clean: bool = False,  # kept for API parity with LaTeXCompiler
    ) -> Optional[Path]:
        """
        Render an HTML resume and compile it to PDF.

        Args:
            output_pdf: Path to resulting PDF file
            template_name: HTML/Jinja2 template filename in template_dir
            context: Dict matching your Resume model (name, experience, etc.)
            clean: Ignored (kept for interface consistency)

        Returns:
            Path to PDF file if successful, None otherwise
        """
        try:
            # Get the current CSS file (reads from env each time)
            css_file = self._get_css_file()

            print(
                f"  Rendering HTML with template {template_name}, css file {css_file}..."
            )

            template = self.env.get_template(template_name)
            html_str = template.render(**context)

            # Ensure output directory exists
            output_pdf.parent.mkdir(parents=True, exist_ok=True)

            # Resolve CSS
            css_path = self.template_dir / css_file
            base_url = str(self.template_dir.resolve())

            if not css_path.exists():
                print(f"  ⚠ CSS file not found: {css_path}")
                print("    PDF will be generated with default styles")
                stylesheets = []
            else:
                print(f"  ✓ Using CSS stylesheet: {css_path}")
                stylesheets = [CSS(filename=str(css_path))]

            print(f"  Generating PDF {output_pdf.name} with WeasyPrint...")

            # HTML(string=...).write_pdf(...) is the recommended pattern
            html_doc = HTML(string=html_str, base_url=base_url)
            html_doc.write_pdf(
                target=str(output_pdf),
                stylesheets=stylesheets,
            )

            if output_pdf.exists():
                print(f"  ✓ PDF created: {output_pdf.name}")
                return output_pdf
            else:
                print("  ✗ PDF not created")
                return None

        except Exception as e:
            print(f"  ✗ WeasyPrint compilation error: {e}")
            return None

    def get_recommended_engine(self, template: str) -> str:
        """Kept for interface symmetry; WeasyPrint doesn't need engine selection."""
        return "weasyprint"
