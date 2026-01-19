"""
Achievement matching for resume tailoring.

Updated for Python 3.14 compatibility.
"""

from collections.abc import Sequence
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..config import PipelineConfig
from ..models import Achievement, CareerProfile, JDRequirements


class AchievementMatcher:
    """Matches candidate achievements to job requirements."""

    def __init__(
        self, base_llm: ChatOpenAI, strong_llm: ChatOpenAI, config: PipelineConfig
    ):
        """
        Initialize achievement matcher.

        Args:
            base_llm: Base language model for initial processing
            strong_llm: Strong language model for final ranking
            config: Pipeline configuration
        """
        self.base_llm = base_llm
        self.strong_llm = strong_llm  # Use strong model for important matching
        self.config = config
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """Initialize matching prompts."""
        self.system_prompt = """You are an expert at matching candidate achievements to job requirements.

Your task:
1. Analyze the job requirements and identify key domains, skills, and experience needs
2. Review the candidate's work history and extract relevant achievements
3. Score and rank achievements by relevance to this specific role
4. Return the top 15-20 most relevant achievements

Scoring criteria:
- Domain match (aerospace, defense, software, etc.)
- Skill alignment (technical skills, tools, methodologies)
- Seniority fit (leadership, scope, team size)
- Impact relevance (metrics that matter for this role)
- Recency (prefer recent achievements unless older ones are highly relevant)

Output format:
Return a JSON array of achievement objects, each with:
{
  "description": "Full achievement description",
  "impact_metric": "Quantified impact (optional)",
  "domain_tags": ["relevant", "domain", "tags"],
  "relevance_score": 0.95  // 0.0 to 1.0
}

Sort by relevance_score descending. Include 15-20 achievements."""

        self.user_prompt = """Job Requirements:
{jd_json}

Candidate Profile:
{profile_summary}

Return top 15-20 achievements as JSON array, sorted by relevance."""

    def match(self, jd: JDRequirements, profile: CareerProfile) -> list[Achievement]:
        """
        Match and rank achievements for a specific job.

        Args:
            jd: Job requirements
            profile: Candidate's career profile

        Returns:
            List of top achievements ranked by relevance
        """
        print(f"\n{'=' * 80}")
        print("ACHIEVEMENT MATCHING")
        print(f"{'=' * 80}\n")

        # Extract all achievements from profile
        all_achievements = self._extract_all_achievements(profile)
        print(f"  Found {len(all_achievements)} total achievements")

        # Use LLM to match and rank
        matched = self._rank_achievements_with_llm(jd, profile, all_achievements)
        print(f"  Selected {len(matched)} top achievements\n")

        return matched

    def _extract_all_achievements(self, profile: CareerProfile) -> list[Achievement]:
        """
        Extract all achievements from career profile.

        Args:
            profile: Career profile

        Returns:
            List of all Achievement objects from work history
        """
        achievements = []

        for job in profile.work:
            # Process highlights as achievements
            if job.highlights:
                for highlight in job.highlights:
                    # Infer domain tags from job context
                    domain_tags = self._infer_domain_tags(job.name, job.position)

                    achievements.append(
                        Achievement(
                            description=highlight,
                            impact_metric=None,  # Extract if present in text
                            domain_tags=domain_tags,
                        )
                    )

            # Process structured achievements if present
            if job.achievements:
                for achievement in job.achievements:
                    if isinstance(achievement, dict):
                        # Structured achievement
                        domain_tags = achievement.get("domain_tags", [])
                        if not domain_tags:
                            domain_tags = self._infer_domain_tags(
                                job.name, job.position
                            )

                        achievements.append(
                            Achievement(
                                description=achievement.get("description", ""),
                                impact_metric=achievement.get("impact_metric"),
                                domain_tags=domain_tags,
                            )
                        )
                    elif isinstance(achievement, str):
                        # Legacy string format
                        domain_tags = self._infer_domain_tags(job.name, job.position)
                        achievements.append(
                            Achievement(
                                description=achievement,
                                impact_metric=None,
                                domain_tags=domain_tags,
                            )
                        )

        return achievements

    def _rank_achievements_with_llm(
        self,
        jd: JDRequirements,
        profile: CareerProfile,
        achievements: Sequence[Achievement],
    ) -> list[Achievement]:
        """
        Use LLM to intelligently rank achievements by relevance.

        Args:
            jd: Job requirements
            profile: Career profile
            achievements: All achievements to rank

        Returns:
            Top-ranked achievements
        """
        if not achievements:
            return []

        prompt = ChatPromptTemplate.from_messages(
            [("system", self.system_prompt), ("user", self.user_prompt)]
        )

        # Use strong LLM for important matching task
        chain = prompt | self.strong_llm

        # Create profile summary
        profile_summary = self._create_profile_summary(profile)

        # Invoke LLM
        try:
            response = chain.invoke(
                {
                    "jd_json": jd.model_dump_json(indent=2),
                    "profile_summary": profile_summary,
                }
            )

            # Parse response
            ranked = self._parse_achievement_response(response.content)
            return ranked[:20]  # Top 20 max

        except Exception as e:
            print(f"  ⚠ LLM ranking failed: {e}")
            # Fallback: return recent achievements
            return list(achievements[:15])

    def _create_profile_summary(self, profile: CareerProfile) -> str:
        """
        Create concise profile summary for LLM matching.

        Args:
            profile: Career profile

        Returns:
            Formatted summary string
        """
        parts = [f"Name: {profile.basics.name}"]

        # Work history
        if profile.work:
            parts.append("\nWork History:")
            for job in profile.work[:5]:  # Recent 5 jobs
                date_range = f"{job.startDate or ''} - {job.endDate or 'Present'}"
                parts.append(f"  {job.position} at {job.name} ({date_range})")

                # Include highlights
                if job.highlights:
                    for highlight in job.highlights[:3]:  # Top 3 per job
                        parts.append(f"    • {highlight}")

        # Skills
        if profile.skills:
            skill_names = [s.name for s in profile.skills[:15]]
            parts.append(f"\nKey Skills: {', '.join(skill_names)}")

        return "\n".join(parts)

    def _infer_domain_tags(self, company: str, position: str) -> list[str]:
        """
        Infer domain tags from job context.

        Args:
            company: Company name
            position: Job position/title

        Returns:
            List of inferred domain tags
        """
        tags = []

        # Combine company and position for analysis
        context = f"{company} {position}".lower()

        # Domain keywords
        domain_map = {
            "aerospace": ["aerospace", "aircraft", "aviation", "flight"],
            "defense": ["defense", "military", "raytheon", "lockheed", "northrop"],
            "software": ["software", "developer", "engineer", "programming"],
            "hardware": ["hardware", "embedded", "firmware", "fpga"],
            "ml_ai": ["machine learning", "ai", "data science"],
            "cloud": ["cloud", "aws", "azure", "devops"],
            "cybersecurity": ["security", "cybersecurity", "infosec"],
        }

        for domain, keywords in domain_map.items():
            if any(kw in context for kw in keywords):
                tags.append(domain)

        return tags if tags else ["general"]

    def _parse_achievement_response(self, content: str) -> list[Achievement]:
        """
        Parse LLM response into Achievement objects.

        Args:
            content: LLM response text

        Returns:
            List of Achievement objects
        """
        import json
        import re

        # Remove markdown code fences
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*$", "", content)
        content = content.strip()

        try:
            data = json.loads(content)

            # Handle both array and object responses
            if isinstance(data, dict):
                data = data.get("achievements", [])

            achievements = []
            for item in data:
                # Skip relevance_score field (not in Achievement model)
                if "relevance_score" in item:
                    del item["relevance_score"]

                achievements.append(Achievement.model_validate(item))

            return achievements

        except Exception as e:
            print(f"  ⚠ Failed to parse achievements: {e}")
            return []
