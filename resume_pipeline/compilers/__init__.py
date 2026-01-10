"""compilation utilities."""

from .latex_compiler import LaTeXCompiler
from .weayprint_compiler import WeazyPrintCompiler

__all__ = ["LaTeXCompiler", "WeazyPrintCompiler"]
COMPILERS = {"latex": LaTeXCompiler, "weasyprint": WeasyPrintCompiler}
