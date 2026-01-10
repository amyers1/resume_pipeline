"""
AI Resume Generation Pipeline

Automatically generate tailored, ATS-optimized resumes for specific job postings.
"""

from .pipeline import ResumePipeline
from .config import PipelineConfig
from .models import (
    Achievement,
    Role,
    CareerProfile,
    JDRequirements,
    StructuredResume,
    CritiqueResult,
)

__version__ = "2.0.0"

__all__ = [
    "ResumePipeline",
    "PipelineConfig",
    "Achievement",
    "Role",
    "CareerProfile",
    "JDRequirements",
    "StructuredResume",
    "CritiqueResult",
]
