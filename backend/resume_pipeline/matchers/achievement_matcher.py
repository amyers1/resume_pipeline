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
2. Review the candidate's achievements WITH their pre-computed domain_match_scores
3. Rank achievements by combining domain match score with other relevance factors
4. Return the top 15-20 most relevant achievements

Scoring criteria (in priority order):
1. Domain match score (PRE-COMPUTED - achievements with higher domain_match_score should rank higher)
2. Skill alignment (technical skills, tools, methodologies mentioned in JD)
3. Seniority fit (leadership scope, team size, budget responsibility)
4. Impact relevance (quantified metrics that demonstrate capability)
5. Recency (prefer recent achievements unless older ones are highly relevant)

IMPORTANT: The domain_match_score is pre-calculated based on overlap between the achievement's
domain_tags and the job's domain_focus. Use this as a primary ranking signal - achievements
with domain_match_score > 0.5 should generally rank higher than those with lower scores.

Output format:
Return a JSON array of achievement objects, each with:
{
  "description": "Full achievement description",
  "impact_metric": "Quantified impact (optional)",
  "domain_tags": ["relevant", "domain", "tags"],
  "relevance_score": 0.95  // 0.0 to 1.0 - your overall relevance assessment
}

Sort by relevance_score descending. Include 15-20 achievements."""

        self.user_prompt = """Job Requirements:
{jd_json}

Candidate Achievements (with pre-computed domain_match_scores):
{achievements_with_scores}

Return top 15-20 achievements as JSON array, sorted by overall relevance."""

    def match(self, jd: JDRequirements, profile: CareerProfile) -> list[Achievement]:
        """
        Match and rank achievements for a specific job.

        Uses domain-weighted pre-filtering to prioritize achievements
        that match the JD's domain_focus before LLM ranking.

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

        # Pre-filter to prioritize domain-matched achievements
        filtered_achievements = self._domain_weighted_filter(jd, all_achievements)
        print(
            f"  After domain filtering: {len(filtered_achievements)} achievements for LLM ranking"
        )

        # Use LLM to match and rank
        matched = self._rank_achievements_with_llm(jd, profile, filtered_achievements)
        print(f"  Selected {len(matched)} top achievements\n")

        return matched

    def _domain_weighted_filter(
        self, jd: JDRequirements, achievements: list[Achievement]
    ) -> list[Achievement]:
        """
        Pre-filter achievements to prioritize those with domain overlap.

        Strategy:
        1. Calculate domain_match_score for each achievement
        2. Ensure high-match achievements (≥50% overlap) are included
        3. Fill remaining slots with other achievements
        4. Limit total to top_k_heuristic from config

        Args:
            jd: Job requirements with domain_focus
            achievements: All extracted achievements

        Returns:
            Filtered list prioritizing domain-matched achievements
        """
        if not jd.domain_focus:
            # No domain focus specified, return all (up to limit)
            return achievements[: self.config.top_k_heuristic]

        jd_domains = set(d.lower() for d in jd.domain_focus)

        # Score all achievements
        scored = []
        for achievement in achievements:
            achievement_domains = set(t.lower() for t in achievement.domain_tags)
            if achievement_domains:
                overlap = len(jd_domains & achievement_domains)
                score = overlap / len(jd_domains) if jd_domains else 0.0
            else:
                score = 0.0
            scored.append((score, achievement))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Separate high-match and low-match
        high_match = [
            (s, a) for s, a in scored if s >= 0.3
        ]  # At least 30% domain overlap
        low_match = [(s, a) for s, a in scored if s < 0.3]

        # Build result: prioritize high-match, fill with low-match
        max_achievements = self.config.top_k_heuristic
        result = [a for _, a in high_match[:max_achievements]]

        # Fill remaining slots with low-match achievements
        remaining_slots = max_achievements - len(result)
        if remaining_slots > 0:
            result.extend([a for _, a in low_match[:remaining_slots]])

        print(
            f"  Domain pre-filter: {len(high_match)} high-match, {len(low_match)} low-match"
        )

        return result

    def _extract_all_achievements(self, profile: CareerProfile) -> list[Achievement]:
        """
        Extract all achievements from career profile.

        Uses existing domain_tags from structured achievements when available,
        only falling back to inference for legacy string-only highlights.

        Args:
            profile: Career profile

        Returns:
            List of all Achievement objects from work history
        """
        achievements = []

        for job in profile.work:
            # Process highlights - these may be strings or structured objects
            if job.highlights:
                for highlight in job.highlights:
                    if isinstance(highlight, dict):
                        # Structured highlight with domain_tags
                        domain_tags = highlight.get("domain_tags", [])
                        if not domain_tags:
                            domain_tags = self._infer_domain_tags(
                                job.name, job.position
                            )
                        achievements.append(
                            Achievement(
                                description=highlight.get("description", ""),
                                impact_metric=highlight.get("impact_metric"),
                                domain_tags=domain_tags,
                                skills=highlight.get("skills", []),
                            )
                        )
                    else:
                        # Legacy string format - infer tags
                        domain_tags = self._infer_domain_tags(job.name, job.position)
                        achievements.append(
                            Achievement(
                                description=highlight,
                                impact_metric=None,
                                domain_tags=domain_tags,
                            )
                        )

            # Process structured achievements if present (preferred source)
            if job.achievements:
                for achievement in job.achievements:
                    if isinstance(achievement, dict):
                        # Structured achievement - use existing domain_tags
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
                                skills=achievement.get("skills", []),
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

        Pre-computes domain_match_score for each achievement based on
        overlap with JD domain_focus, then passes to LLM for final ranking.

        Args:
            jd: Job requirements
            profile: Career profile
            achievements: All achievements to rank

        Returns:
            Top-ranked achievements
        """
        if not achievements:
            return []

        # Pre-compute domain match scores
        jd_domains = set(d.lower() for d in jd.domain_focus)
        achievements_with_scores = []

        for achievement in achievements:
            # Calculate domain overlap score
            achievement_domains = set(t.lower() for t in achievement.domain_tags)
            if jd_domains and achievement_domains:
                overlap = len(jd_domains & achievement_domains)
                domain_match_score = overlap / len(jd_domains)
            else:
                domain_match_score = 0.0

            achievements_with_scores.append(
                {
                    "description": achievement.description,
                    "impact_metric": achievement.impact_metric,
                    "domain_tags": achievement.domain_tags,
                    "domain_match_score": round(domain_match_score, 2),
                }
            )

        # Sort by domain_match_score for initial ordering (LLM will refine)
        achievements_with_scores.sort(
            key=lambda x: x["domain_match_score"], reverse=True
        )

        # Log domain matching stats
        high_match = sum(
            1 for a in achievements_with_scores if a["domain_match_score"] >= 0.5
        )
        print(
            f"  Domain matching: {high_match}/{len(achievements_with_scores)} achievements with ≥50% domain overlap"
        )

        prompt = ChatPromptTemplate.from_messages(
            [("system", self.system_prompt), ("user", self.user_prompt)]
        )

        # Use strong LLM for important matching task
        chain = prompt | self.strong_llm

        # Invoke LLM with achievements + scores
        try:
            import json

            response = chain.invoke(
                {
                    "jd_json": jd.model_dump_json(indent=2),
                    "achievements_with_scores": json.dumps(
                        achievements_with_scores, indent=2
                    ),
                }
            )

            # Parse response
            ranked = self._parse_achievement_response(response.content)
            return ranked[:20]  # Top 20 max

        except Exception as e:
            print(f"  ⚠ LLM ranking failed: {e}")
            # Fallback: return achievements sorted by domain_match_score
            fallback = [
                Achievement(
                    description=a["description"],
                    impact_metric=a["impact_metric"],
                    domain_tags=a["domain_tags"],
                )
                for a in achievements_with_scores[:15]
            ]
            return fallback

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

        # Expanded domain keywords matching career_profile.json tags
        domain_map = {
            # Core Technical Domains
            "EW": [
                "electronic warfare",
                "ew ",
                "jamming",
                "countermeasures",
                "threat library",
            ],
            "ISR": [
                "isr",
                "intelligence",
                "surveillance",
                "reconnaissance",
                "sigint",
                "collection",
            ],
            "RF": [
                "rf ",
                "radio frequency",
                "antenna",
                "electromagnetic",
                "signal processing",
            ],
            "Radar": ["radar", "synthetic aperture", "sar ", "aesa"],
            "Cyber": ["cyber", "cybersecurity", "infosec", "penetration", "rmf", "ato"],
            "PNT": ["pnt", "gps", "navigation", "positioning", "timing"],
            "Satellite_Ops": ["satellite", "spacecraft", "on-orbit", "launch", "space"],
            "C2": ["command and control", "c2 ", "c4isr"],
            # Engineering & Development
            "Systems_Engineering": [
                "systems engineer",
                "requirements",
                "integration",
                "verification",
            ],
            "Electrical_Engineering": [
                "electrical engineer",
                "circuit",
                "power systems",
            ],
            "Software_Dev": ["software", "developer", "programming", "python", "code"],
            "Data_Science": [
                "data science",
                "analytics",
                "machine learning",
                "ai ",
                "ml ",
            ],
            "Test_Eval": [
                "test",
                "evaluation",
                "t&e",
                "verification",
                "validation",
                "hitl",
            ],
            "R&D": ["research", "r&d", "laboratory", "afrl", "darpa"],
            # Leadership & Management
            "Program_Mgmt": ["program manag", "portfolio", "acquisition", "budget"],
            "Technical_Leadership": ["technical lead", "chief engineer", "architect"],
            "Executive_Leadership": ["director", "deputy", "chief", "commander"],
            # Operations
            "Operations": ["operations", "mission", "deployment", "operational"],
            "Flight_Test": ["flight test", "developmental test", "airborne"],
            # Industries
            "Defense": [
                "defense",
                "military",
                "dod",
                "air force",
                "army",
                "navy",
                "usaf",
            ],
            "Aerospace": [
                "aerospace",
                "aircraft",
                "aviation",
                "lockheed",
                "northrop",
                "raytheon",
                "boeing",
            ],
            # Technologies
            "Cloud": ["cloud", "aws", "azure", "gcp", "devops"],
            "Automation": ["automation", "automated", "scripting"],
            "Sensors": ["sensor", "detector", "imaging"],
            "UAS": ["uas", "uav", "drone", "unmanned"],
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
