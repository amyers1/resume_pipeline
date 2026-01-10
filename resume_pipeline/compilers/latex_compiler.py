"""
LaTeX compilation utilities.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional


class LaTeXCompiler:
    """Compiles LaTeX documents to PDF."""

    def __init__(self, template_dir: Optional[Path] = None, fonts_dir: Optional[Path] = None):
        """
        Initialize LaTeX compiler.

        Args:
            template_dir: Directory containing template .cls files
            fonts_dir: Directory containing custom fonts (optional)
        """
        self.pdflatex_path = shutil.which("pdflatex")
        self.xelatex_path = shutil.which("xelatex")
        self.template_dir = template_dir or Path("templates")
        self.fonts_dir = fonts_dir or Path("fonts")

        if not self.xelatex_path:
            print("  ⚠ xelatex not found - PDF compilation disabled")
            print("    Install: apt-get install texlive-xetex")

    def compile(
        self,
        tex_file: Path,
        engine: str = "xelatex",
        clean: bool = True
    ) -> Optional[Path]:
        """
        Compile LaTeX file to PDF.

        Args:
            tex_file: Path to .tex file
            engine: LaTeX engine ('xelatex' or 'pdflatex')
            clean: Remove auxiliary files after compilation

        Returns:
            Path to PDF file if successful, None otherwise
        """
        if engine == "xelatex" and not self.xelatex_path:
            print(f"  ✗ xelatex not available, skipping PDF compilation")
            return None

        if engine == "pdflatex" and not self.pdflatex_path:
            print(f"  ✗ pdflatex not available, skipping PDF compilation")
            return None

        print(f"  Compiling {tex_file.name} with {engine}...")

        # Get working directory
        work_dir = tex_file.parent

        # Copy template files to output directory
        self._copy_template_files(work_dir)

        # Copy fonts if using xelatex and fonts exist
        if engine == "xelatex" and self.fonts_dir.exists():
            self._copy_fonts(work_dir)

        # Choose compiler
        compiler = self.xelatex_path if engine == "xelatex" else self.pdflatex_path

        try:
            # Run compilation (twice for references)
            for run in range(2):
                result = subprocess.run(
                    [
                        compiler,
                        "-interaction=nonstopmode",
                        "-halt-on-error",
                        tex_file.name
                    ],
                    cwd=work_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    print(f"  ✗ Compilation failed on run {run + 1}")
                    # Show relevant error lines
                    error_lines = result.stdout.split('\n')
                    # Find actual error (look for "!" lines)
                    error_context = [line for line in error_lines if line.startswith('!') or 'Error' in line]
                    if error_context:
                        print(f"    Error output:")
                        for line in error_context[:10]:  # Show first 10 error lines
                            print(f"      {line}")
                    else:
                        # Show last 20 lines if no specific errors found
                        print(f"    Last lines of output:")
                        for line in error_lines[-20:]:
                            if line.strip():
                                print(f"      {line}")
                    return None

            # Check for PDF
            pdf_file = tex_file.with_suffix(".pdf")
            if pdf_file.exists():
                print(f"  ✓ PDF created: {pdf_file.name}")

                # Clean auxiliary files
                if clean:
                    self._clean_aux_files(tex_file)

                return pdf_file
            else:
                print(f"  ✗ PDF not created")
                return None

        except subprocess.TimeoutExpired:
            print(f"  ✗ Compilation timeout")
            return None
        except Exception as e:
            print(f"  ✗ Compilation error: {e}")
            return None

    def _copy_template_files(self, work_dir: Path):
        """Copy template .cls and .sty files to output directory."""
        if not self.template_dir.exists():
            print(f"  ⚠ Template directory not found: {self.template_dir}")
            print(f"    LaTeX compilation may fail if template files are missing")
            return

        # Find all .cls and .sty files
        template_files = list(self.template_dir.glob("*.cls")) + \
                        list(self.template_dir.glob("*.sty"))

        if not template_files:
            print(f"  ⚠ No template files found in {self.template_dir}")
            return

        # Copy to output directory
        for template_file in template_files:
            dest = work_dir / template_file.name
            if not dest.exists():
                shutil.copy2(template_file, dest)
                print(f"    Copied template: {template_file.name}")

    def _copy_fonts(self, work_dir: Path):
        """Copy custom fonts to output directory for XeLaTeX."""
        if not self.fonts_dir.exists():
            return

        # Find font files
        font_extensions = ['*.ttf', '*.otf', '*.TTF', '*.OTF']
        font_files = []
        for ext in font_extensions:
            font_files.extend(self.fonts_dir.glob(ext))

        if not font_files:
            return

        # Create fonts subdirectory in output
        fonts_dest = work_dir / "fonts"
        fonts_dest.mkdir(exist_ok=True)

        # Copy fonts
        for font_file in font_files:
            dest = fonts_dest / font_file.name
            if not dest.exists():
                shutil.copy2(font_file, dest)

        if font_files:
            print(f"    Copied {len(font_files)} font file(s)")

    def _clean_aux_files(self, tex_file: Path):
        """Remove auxiliary LaTeX files."""
        aux_extensions = [".aux", ".log", ".out", ".toc", ".fls", ".fdb_latexmk"]

        for ext in aux_extensions:
            aux_file = tex_file.with_suffix(ext)
            if aux_file.exists():
                aux_file.unlink()

    def get_recommended_engine(self, template: str) -> str:
        """Get recommended LaTeX engine for template."""
        if template.lower() == "awesome-cv":
            return "xelatex"
        else:
            return "xelatex"

    def check_fonts(self) -> dict:
        """
        Check for required fonts on the system.

        Returns:
            Dict with font availability status
        """
        required_fonts = {
            "Roboto": ["Roboto-Regular", "Roboto"],
            "Roboto Slab": ["RobotoSlab-Regular", "Roboto Slab"],
            "Source Sans Pro": ["SourceSansPro-Regular", "Source Sans Pro"],
        }

        font_status = {}

        # Try to check using fc-list
        fc_list = shutil.which("fc-list")
        if fc_list:
            try:
                result = subprocess.run(
                    [fc_list, ":", "family"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                available_fonts = result.stdout.lower()

                for font_name, variants in required_fonts.items():
                    found = any(variant.lower() in available_fonts for variant in variants)
                    font_status[font_name] = found

            except Exception:
                # Can't check fonts, assume they're available
                font_status = {name: None for name in required_fonts}
        else:
            # fc-list not available
            font_status = {name: None for name in required_fonts}

        return font_status
