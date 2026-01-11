"""
Resume critique and iterative refinement.
"""

from langchain_core.language_models.chat_models import BaseChatModel # Changed
from langchain_core.prompts import ChatPromptTemplate
from ..models import CritiqueResult
from ..config import PipelineConfig


class ResumeCritic:
    """Critiques resumes and performs iterative refinement."""

    def __init__(self, llm: BaseChatModel, config: PipelineConfig): # Changed type hint
            self.llm = llm
            self.config = config
            self._setup_prompts()

    def _setup_prompts(self):
        """Initialize critique and refinement prompts."""
        self.critic_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You evaluate resumes against job descriptions for senior technical roles. "
             "Assess: (1) JD alignment - coverage of must-haves, keyword usage, seniority fit; "
             "(2) Resume quality - ATS safety, structure, clarity, impact, chronology; "
             "(3) Length - must be ≤2 pages when rendered (~1000 words max). "
             "Score generously if content is strong but slightly under keyword threshold - "
             "brevity and impact matter more than keyword density. "
             "Output JSON only with: score (0-1), jd_keyword_coverage (0-1), ats_ok (bool), "
             "length_ok (bool), strengths (list), weaknesses (list), suggestions (list)."),
            ("user",
             "Job requirements:\n{jd_json}\n\nResume:\n{resume}\n\n"
             "Evaluate and return CritiqueResult JSON. Be generous with scoring if content is strong.")
        ])

        self.refine_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You revise resumes based on critiques. Preserve structure and factual accuracy. "
             "NEVER fabricate skills, metrics, or experience. Address weaknesses and suggestions "
             "while maintaining all verified content. CRITICAL: Keep resume ≤2 pages (~1000 words). "
             "Prefer concise, high-impact bullets over verbose descriptions. "
             "If already at length limit, only improve clarity and keyword usage - don't expand. "
             "Output revised resume in markdown only."),
            ("user",
             "Job requirements:\n{jd_json}\n\nOriginal resume:\n{resume}\n\n"
             "Critique:\n{critique}\n\n"
             "Revise addressing critique. MUST stay ≤2 pages. Markdown only.")
        ])

    def critique_and_refine(
        self,
        draft: str,
        jd: JDRequirements
    ) -> tuple[str, dict]:
        """
        Iteratively critique and refine resume.

        Args:
            draft: Initial resume draft
            jd: Job requirements

        Returns:
            Tuple of (final_resume, critique_dict)
        """
        current_resume = draft
        last_critique = None

        for iteration in range(1, self.config.max_critique_loops + 1):
            print(f"  Iteration {iteration}/{self.config.max_critique_loops} "
                  f"(model: {self.config.base_model})...")

            # Critique
            critique = self._critique(current_resume, jd)
            last_critique = critique.model_dump()

            print(f"    Score: {critique.score:.3f} | "
                  f"Coverage: {critique.jd_keyword_coverage:.3f} | "
                  f"Length OK: {critique.length_ok}")

            # Check if we meet threshold (relaxed criteria)
            meets_threshold = (
                critique.score >= self.config.critique_threshold and
                critique.jd_keyword_coverage >= (self.config.critique_threshold - 0.1) and
                critique.length_ok
            )

            if meets_threshold:
                print(f"  ✓ Quality threshold met!")
                break

            # Last iteration - stop even if below threshold
            if iteration == self.config.max_critique_loops:
                print(f"  → Max iterations reached (best effort)")
                break

            # Refine
            current_resume = self._refine(current_resume, critique, jd)

        return current_resume, last_critique

    def _critique(self, resume: str, jd: JDRequirements) -> CritiqueResult:
        """Evaluate resume quality."""
        chain = self.critic_prompt | self.llm.with_structured_output(CritiqueResult)
        critique = chain.invoke({
            "jd_json": jd.model_dump_json(),
            "resume": resume
        })
        return critique

    def _refine(
        self,
        resume: str,
        critique: CritiqueResult,
        jd: JDRequirements
    ) -> str:
        """Improve resume based on critique."""
        chain = self.refine_prompt | self.llm
        refined = chain.invoke({
            "jd_json": jd.model_dump_json(),
            "resume": resume,
            "critique": critique.model_dump_json(indent=2)
        })
        return refined.content if hasattr(refined, "content") else str(refined)
