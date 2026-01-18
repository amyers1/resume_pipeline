"""
Achievement matching and ranking against job requirements.
"""

from typing import List, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..models import Achievement, JDRequirements, CareerProfile, RankedAchievementsResponse
from ..config import PipelineConfig


class AchievementMatcher:
    """Matches and ranks candidate achievements against job requirements."""

    def __init__(self, base_llm: ChatOpenAI, strong_llm: ChatOpenAI, config: PipelineConfig):
        self.base_llm = base_llm
        self.strong_llm = strong_llm
        self.config = config
        self._setup_prompts()

    def _setup_prompts(self):
        """Initialize LLM prompts."""
        self.rerank_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You match candidate achievements to job requirements. "
             "Select and rank the top 10-12 achievements that best demonstrate "
             "the candidate's fit for the role. Consider relevance, impact, and "
             "recency. Return JSON with 'items' array containing 'index' and 'reason' fields."),
            ("user",
             "Job requirements:\n{jd_json}\n\n"
             "Candidate achievements:\n{achievements_text}\n\n"
             "Select top {top_k} achievements by index with brief reasoning.")
        ])

    def match(self, jd: JDRequirements, profile: CareerProfile) -> List[Achievement]:
        """
        Match and rank achievements against job requirements.

        Args:
            jd: Structured job requirements
            profile: Candidate career profile

        Returns:
            List of top-ranked achievements
        """
        # Step 1: Heuristic scoring
        scored = self._score_all_achievements(profile, jd)
        candidates = [a for a, _ in scored[:self.config.top_k_heuristic]]

        # Step 2: LLM re-ranking
        ranked = self._rerank_with_llm(candidates, jd)

        return ranked

    def _score_all_achievements(
        self,
        profile: CareerProfile,
        jd: JDRequirements
    ) -> List[Tuple[Achievement, float]]:
        """Score all achievements using heuristic method."""
        scored = []
        for role in profile.roles:
            for ach in role.achievements:
                score = self._score_achievement(ach, jd)
                if score > 0:
                    scored.append((ach, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def _score_achievement(self, ach: Achievement, jd: JDRequirements) -> float:
        """
        Heuristic scoring of single achievement.

        Scoring weights:
        - Must-have skills: 3.0
        - Nice-to-have skills: 1.5
        - Domain alignment: 2.5
        - Keywords: 0.5
        """
        text = (ach.description + " " + (ach.impact_metric or "")).lower()
        score = 0.0

        # Must-have skills (high weight)
        for skill in jd.must_have_skills:
            if skill.lower().split()[0] in text:
                score += 3.0

        # Nice-to-have skills
        for skill in jd.nice_to_have_skills:
            if skill.lower().split()[0] in text:
                score += 1.5

        # Keywords
        for kw in jd.keywords:
            if kw.lower() in text:
                score += 0.5

        # Domain alignment (high weight)
        for tag in ach.domain_tags:
            if tag.lower() in [d.lower() for d in jd.domain_focus]:
                score += 2.5

        return score

    def _rerank_with_llm(
        self,
        candidates: List[Achievement],
        jd: JDRequirements
    ) -> List[Achievement]:
        """Use LLM to re-rank top candidates."""
        # Format achievements for LLM
        achievements_text = "\n".join([
            f"[{i}] {ach.description}\n"
            f"    Impact: {ach.impact_metric or 'N/A'}\n"
            f"    Domains: {', '.join(ach.domain_tags)}"
            for i, ach in enumerate(candidates)
        ])

        # Get LLM ranking
        chain = self.rerank_prompt | self.strong_llm.with_structured_output(
            RankedAchievementsResponse
        )
        resp = chain.invoke({
            "jd_json": jd.model_dump_json(),
            "achievements_text": achievements_text,
            "top_k": self.config.top_k_final,
        })

        # Extract ranked achievements
        ranked_indices = [
            r.index for r in resp.items[:self.config.top_k_final]
            if 0 <= r.index < len(candidates)
        ]

        return [candidates[i] for i in ranked_indices]
