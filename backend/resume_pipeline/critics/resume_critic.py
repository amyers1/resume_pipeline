"""
Resume critique and iterative refinement.

Updated for Python 3.14 compatibility.
"""

import json
from typing import Any

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate

from ..config import PipelineConfig
from ..models import CritiqueResult, JDRequirements


class ResumeCritic:
    """Critiques resumes and performs iterative refinement."""

    def __init__(self, llm: BaseChatModel, config: PipelineConfig):
        self.llm = llm
        self.config = config
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """Initialize critique and refinement prompts."""
        self.critic_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You evaluate resumes against job descriptions for senior technical roles. "
                    "Assess: (1) JD alignment - coverage of must-haves, keyword usage, seniority fit; "
                    "(2) Resume quality - ATS safety, structure, clarity, impact, chronology; "
                    "(3) Length - must be ≤2 pages when rendered (~1000 words max). "
                    "Score generously if content is strong but slightly under keyword threshold - "
                    "brevity and impact matter more than keyword density. "
                    "Output JSON only with: score (0-1), jd_keyword_coverage (0-1), ats_ok (bool), "
                    "length_ok (bool), strengths (list), weaknesses (list), suggestions (list).",
                ),
                (
                    "user",
                    "Job requirements:\n{jd_json}\n\nResume:\n{resume}\n\n"
                    "Evaluate and return CritiqueResult JSON. Be generous with scoring if content is strong.",
                ),
            ]
        )

        self.refine_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You revise resumes based on critiques. Preserve structure and factual accuracy. "
                    "NEVER fabricate skills, metrics, or experience. Address weaknesses and suggestions "
                    "while maintaining all verified content. CRITICAL: Keep resume ≤2 pages (~1000 words). "
                    "Prefer concise, high-impact bullets over verbose descriptions. "
                    "If already at length limit, only improve clarity and keyword usage - don't expand. "
                    "Output revised resume in markdown only.",
                ),
                (
                    "user",
                    "Job requirements:\n{jd_json}\n\nOriginal resume:\n{resume}\n\n"
                    "Critique:\n{critique}\n\n"
                    "Revise addressing critique. MUST stay ≤2 pages. Markdown only.",
                ),
            ]
        )

    def critique_and_refine(
        self, draft: str, jd: JDRequirements
    ) -> tuple[str, dict[str, Any]]:
        """
        Iteratively critique and refine resume.

        Args:
            draft: Initial resume draft in markdown
            jd: Job requirements to evaluate against

        Returns:
            Tuple of (final_resume, critique_results_dict)
        """
        current_resume = draft
        all_critiques = []
        max_loops = self.config.max_critique_loops

        print(f"\n{'=' * 80}")
        print("CRITIQUE & REFINEMENT")
        print(f"{'=' * 80}\n")

        for iteration in range(max_loops):
            print(f"  Loop {iteration + 1}/{max_loops}")

            # Critique current version
            critique = self._critique_resume(current_resume, jd)
            all_critiques.append(critique)

            # Log critique results
            self._log_critique(critique, iteration + 1)

            # Check if quality threshold met
            if (
                critique.score >= self.config.min_quality_score / 10
                and critique.ats_ok
                and critique.length_ok
            ):
                print(f"  ✓ Quality threshold met (score: {critique.score:.2f})")
                break

            # If not last iteration, refine
            if iteration < max_loops - 1:
                print(f"  → Refining based on feedback...")
                current_resume = self._refine_resume(current_resume, jd, critique)
            else:
                print(f"  ⚠ Max iterations reached")

        # Return final resume and aggregated critique data
        final_critique = {
            "iterations": len(all_critiques),
            "final_score": all_critiques[-1].score,
            "final_ats_ok": all_critiques[-1].ats_ok,
            "final_length_ok": all_critiques[-1].length_ok,
            "final_keyword_coverage": all_critiques[-1].jd_keyword_coverage,
            "all_critiques": [c.model_dump() for c in all_critiques],
        }

        return current_resume, final_critique

    def _critique_resume(self, resume: str, jd: JDRequirements) -> CritiqueResult:
        """
        Critique a resume against job requirements.

        Args:
            resume: Resume text in markdown
            jd: Job requirements

        Returns:
            Structured critique results
        """
        chain = self.critic_prompt | self.llm

        response = chain.invoke(
            {
                "jd_json": jd.model_dump_json(indent=2),
                "resume": resume,
            }
        )

        # Parse LLM response into CritiqueResult
        try:
            critique_data = self._parse_json_response(response.content)
            return CritiqueResult.model_validate(critique_data)
        except Exception as e:
            print(f"  ⚠ Failed to parse critique: {e}")
            # Return default critique on parse failure
            return CritiqueResult(
                score=0.5,
                ats_ok=True,
                length_ok=True,
                jd_keyword_coverage=0.5,
                strengths=["Unable to parse critique"],
                weaknesses=[],
                suggestions=["Manual review recommended"],
            )

    def _refine_resume(
        self, resume: str, jd: JDRequirements, critique: CritiqueResult
    ) -> str:
        """
        Refine resume based on critique feedback.

        Args:
            resume: Current resume text
            jd: Job requirements
            critique: Critique results with suggestions

        Returns:
            Refined resume text
        """
        chain = self.refine_prompt | self.llm

        # Format critique for LLM
        critique_text = self._format_critique_for_llm(critique)

        response = chain.invoke(
            {
                "jd_json": jd.model_dump_json(indent=2),
                "resume": resume,
                "critique": critique_text,
            }
        )

        return response.content if hasattr(response, "content") else str(response)

    def _log_critique(self, critique: CritiqueResult, iteration: int) -> None:
        """
        Log critique results to console.

        Args:
            critique: Critique results
            iteration: Current iteration number
        """
        print(f"    Score: {critique.score:.2f}/1.0")
        print(f"    Keyword Coverage: {critique.jd_keyword_coverage:.1%}")
        print(f"    ATS Safe: {'✓' if critique.ats_ok else '✗'}")
        print(f"    Length OK: {'✓' if critique.length_ok else '✗'}")

        if critique.strengths:
            print(f"    Strengths:")
            for strength in critique.strengths[:2]:  # Show top 2
                print(f"      • {strength}")

        if critique.weaknesses:
            print(f"    Weaknesses:")
            for weakness in critique.weaknesses[:2]:  # Show top 2
                print(f"      • {weakness}")

    def _format_critique_for_llm(self, critique: CritiqueResult) -> str:
        """
        Format critique results as readable text for LLM refinement.

        Args:
            critique: Structured critique results

        Returns:
            Formatted critique text
        """
        parts = [
            f"Score: {critique.score:.2f}/1.0",
            f"Keyword Coverage: {critique.jd_keyword_coverage:.1%}",
            f"ATS Safe: {critique.ats_ok}",
            f"Length OK: {critique.length_ok}",
        ]

        if critique.weaknesses:
            parts.append("\nWeaknesses:")
            parts.extend(f"- {w}" for w in critique.weaknesses)

        if critique.suggestions:
            parts.append("\nSuggestions:")
            parts.extend(f"- {s}" for s in critique.suggestions)

        return "\n".join(parts)

    def _parse_json_response(self, content: str) -> dict[str, Any]:
        """
        Parse JSON from LLM response, handling markdown code fences.

        Args:
            content: LLM response text

        Returns:
            Parsed JSON as dictionary
        """
        import re

        # Remove markdown code fences if present
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*$", "", content)
        content = content.strip()

        return json.loads(content)
