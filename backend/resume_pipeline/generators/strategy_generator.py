"""
Resume strategy generator (Hiring Manager persona).

Generates strategic direction for resume drafting based on job requirements
and candidate profile summary.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..models import CareerProfile, JDRequirements


class StrategyGenerator:
    """Generates strategic resume direction from hiring manager perspective."""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """Initialize strategy generation prompts."""
        self.system_prompt = """You are an experienced Hiring Manager with deep expertise in defense/aerospace engineering recruitment.

Your role is to analyze job requirements and candidate profiles to provide strategic direction for resume optimization.

ANALYSIS FRAMEWORK:
1. Identify the top 3 specific themes the candidate must emphasize based on the job description
2. Identify the one critical "Red Flag" that could disqualify the candidate and must be proactively mitigated

STRATEGIC THEMES:
- Focus on domain expertise, technical capabilities, leadership scope, and measurable impact
- Consider industry-specific terminology and key qualifications
- Prioritize recent (8-10 years) experience that aligns with role requirements

RED FLAG MITIGATION:
- Identify gaps, missing qualifications, or potential concerns
- Suggest how to reframe or contextualize these issues
- Consider career transitions, employment gaps, or skill mismatches

OUTPUT FORMAT - EXACTLY 4 BULLETS:
• Theme 1: [Specific theme to emphasize]
• Theme 2: [Specific theme to emphasize]
• Theme 3: [Specific theme to emphasize]
• Red Flag: [Critical concern to address] + Mitigation: [How to address it]

Keep each bullet concise (1-2 sentences). Be specific and actionable."""

        self.user_prompt = """Job Description:
{jd_summary}

Candidate Career Profile Summary:
{profile_summary}

Based on this job description and candidate profile, what are the strategic priorities for this resume?

Provide exactly 4 bullets in the specified format."""

    def generate(self, jd: JDRequirements, profile: CareerProfile) -> str:
        """
        Generate resume strategy from hiring manager perspective.

        Args:
            jd: Job requirements extracted from job description
            profile: Candidate's career profile

        Returns:
            Strategic direction text (4-bullet strategy)
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.system_prompt), ("user", self.user_prompt)]
        )

        chain = prompt | self.llm

        # Create concise summaries for the LLM
        jd_summary = self._summarize_jd(jd)
        profile_summary = self._summarize_profile(profile)

        response = chain.invoke({
            "jd_summary": jd_summary,
            "profile_summary": profile_summary,
        })

        return response.content if hasattr(response, "content") else str(response)

    def _summarize_jd(self, jd: JDRequirements) -> str:
        """Create concise JD summary for strategy generation."""
        parts = [
            f"Role: {jd.role_title}",
            f"Company: {jd.company}",
        ]

        if jd.seniority_level:
            parts.append(f"Seniority: {jd.seniority_level}")

        if jd.domain_focus:
            parts.append(f"Domain Focus: {', '.join(jd.domain_focus)}")

        if jd.must_have_skills:
            parts.append(f"Must-Have Skills: {', '.join(jd.must_have_skills)}")

        if jd.key_responsibilities:
            parts.append("Key Responsibilities:")
            for resp in jd.key_responsibilities[:5]:  # Top 5
                parts.append(f"  - {resp}")

        return "\n".join(parts)

    def _summarize_profile(self, profile: CareerProfile) -> str:
        """Create concise profile summary for strategy generation."""
        parts = [
            f"Candidate: {profile.basics.name}",
        ]

        if profile.basics.label:
            parts.append(f"Current Title: {profile.basics.label}")

        if profile.basics.summary:
            parts.append(f"Professional Summary: {profile.basics.summary}")

        if profile.work:
            parts.append("\nRecent Experience:")
            # Get 2 most recent roles
            recent_work = profile.work[:2]
            for job in recent_work:
                parts.append(f"  - {job.position} at {job.name}")
                if job.highlights:
                    for highlight in job.highlights[:2]:
                        parts.append(f"    • {highlight}")

        if profile.skills:
            top_skills = [s.name for s in profile.skills[:8]]
            parts.append(f"\nKey Skills: {', '.join(top_skills)}")

        return "\n".join(parts)
