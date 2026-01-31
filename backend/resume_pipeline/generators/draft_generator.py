"""
Resume draft generation with experience grouping.

Updated for Python 3.14 compatibility.
"""

import json
from collections.abc import Sequence

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..config import PipelineConfig
from ..models import Achievement, CareerProfile, JDRequirements


class DraftGenerator:
    """Generates initial resume drafts with proper structure and grouping."""

    def __init__(self, llm: ChatOpenAI, config: PipelineConfig):
        self.llm = llm
        self.config = config
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        """Initialize generation prompts."""
        self.system_prompt = """You are an expert ATS-optimized resume writer for senior defense/aerospace engineers.

CRITICAL RULES - ACCURACY AND TRUTH:
1. NEVER fabricate skills, tools, certifications, or experience not in the input data
2. NEVER invent metrics, dollar amounts, team sizes, or quantitative claims
3. NEVER add technologies or frameworks not explicitly present in achievements
4. Preserve ALL factual metrics exactly as provided
5. When rephrasing, maintain the substance and scope of original claims

CIVILIAN TRANSLATION PROTOCOL (STRICT):
1. Translate "Commander" to "Director" or "Team Lead" based on team size.
2. Translate "Flight" to "Department" or "Technical Team".
3. Translate "Squadron" to "Organization" or "Business Unit".
4. Translate "Materiel Leader" to "Senior Program Manager".
5. Translate "Executive Officer" to "Chief of Staff".
6. DO NOT use military ranks (Lt Col, Major) in the body text; use functional titles.

STRUCTURE (ATS-safe markdown only):
- Header: name, role title, location, email, phone, LinkedIn (NO repetition elsewhere)
- # Full Name
- ## Professional Summary (2-3 sentences; NO contact info; emphasize recent 8-10 years)
- ## Core Competencies (8-12 items; only verified skills from input)
- ## Experience (reverse chronological)
  - Recent roles (last 8-10 years): 4-6 bullets each, detailed
  - Other Relevant Experience: Grouped section for 2006-2016 roles, 2-3 bullets each
- ## Education (reverse chronological)
- ## Certifications (only real certifications)
- ## Awards (3-5 major recognitions only)

LENGTH CONSTRAINT - CRITICAL:
- Target 2 pages maximum when rendered
- Be concise and impactful - quality over quantity
- Professional Summary: 2-3 sentences maximum
- Recent roles: 4-6 bullets (not 8-10)
- Grouped roles: 2-3 bullets each
- Avoid redundancy across bullets

EXPERIENCE STRATEGY:
- Treat ALL provided roles as significant professional experience.
- DO NOT use an "Other Relevant Experience" grouping section.
- Recent roles (last 10 years): 4-6 high-impact bullets per role.
- Older roles (10+ years): 2-4 technical bullets per role, focusing on hard skills (Engineering, Test, Research).
- Maintain reverse chronological order for the entire career history.

CONTEXTUAL BACKGROUND USAGE:
You are provided with a "Candidate Biography" which contains the full narrative history.
- USE this biography to understand the technical depth, specific equipment (e.g., "MC-130W", "GPS III"), and strategic context of the roles.
- USE this to flesh out "Key Achievements" if the structured data is too brief.
- DO NOT invent skills. If the biography says "managed software team," do not assume "React" or "AWS" unless explicitly stated.
- IF a job requirement asks for a skill (e.g., "Earned Value Management") and it appears in the biography but not the structured profile, YOU MAY INCLUDE IT.

CONTENT REQUIREMENTS:
- Professional Summary: Focus on last 8-10 years, key domains, scope, value proposition
- Core Competencies: ONLY skills/domains clearly supported by input data
- Experience bullets: action + scope + measurable impact
- Tailor to JD: prioritize matched skills and achievements
- Use JD keywords naturally throughout
- Maintain professional tone for senior technical leadership

OUTPUT: Complete resume in markdown. No commentary. Strict 2-page target."""

        self.user_prompt = """Job requirements:
{jd_json}

Candidate Biography (Source of Truth for Context):
{biography}

Candidate profile:
{profile_context}

Top achievements for this role:
{achievements_json}

Contact info (header only):
Name: {name}
Email: {email}
Phone: {phone}
Location: {location}
LinkedIn: {linkedin}
Security Clearance: {clearance}

STRATEGIC DIRECTION:
{strategy_text}

IMPORTANT: Current year is {current_year}.
List ALL roles in the "Experience" section in reverse chronological order.
Ensure older roles (prior to 2016) retain specific technical details (e.g., specific weapon systems, coding languages, engineering metrics) to prove long-term technical depth.

Generate complete ATS-optimized resume in markdown. Target 2 pages maximum."""

    def generate(
        self,
        jd: JDRequirements,
        profile: CareerProfile,
        achievements: Sequence[Achievement],
        strategy: str | None = None,
    ) -> str:
        """
        Generate resume draft.

        Args:
            jd: Job requirements extracted from job description
            profile: Candidate's career profile
            achievements: Matched achievements relevant to this job
            strategy: Optional strategic direction from StrategyGenerator

        Returns:
            Resume draft in markdown format
        """
        prompt = ChatPromptTemplate.from_messages(
            [("system", self.system_prompt), ("user", self.user_prompt)]
        )

        chain = prompt | self.llm

        # Extract LinkedIn URL from profile
        linkedin_url = self._extract_linkedin(profile)

        # Format location string
        location_str = self._format_location(profile)

        # Use profile's to_prompt_string() method for clean LLM context
        profile_context = profile.to_prompt_string()

        # Format strategy text (use default if not provided)
        strategy_text = (
            strategy
            if strategy
            else "Follow best practices for ATS-optimized resume writing."
        )

        bio = profile.biography or profile.summary or "No biography provided."

        # Invoke LLM with structured data
        response = chain.invoke(
            {
                "jd_json": jd.model_dump_json(indent=2),
                "biography": bio,
                "profile_context": profile_context,
                "achievements_json": json.dumps(
                    [a.model_dump() for a in achievements], indent=2
                ),
                # Contact information
                "name": profile.basics.name,
                "email": profile.basics.email or "",
                "phone": profile.basics.phone or "",
                "location": location_str,
                "linkedin": linkedin_url,
                "clearance": profile.basics.clearance or "",
                "current_year": self.config.current_year,
                "strategy_text": strategy_text,
            }
        )

        # Extract content from response
        return response.content if hasattr(response, "content") else str(response)

    def _extract_linkedin(self, profile: CareerProfile) -> str:
        """
        Extract LinkedIn URL from profile.

        Prefers the dedicated linkedin field, falls back to searching profiles[].

        Returns:
            LinkedIn URL or empty string if not found
        """
        if profile.basics.linkedin:
            return profile.basics.linkedin

        if not profile.basics.profiles:
            return ""

        for social_profile in profile.basics.profiles:
            if social_profile.network and "linkedin" in social_profile.network.lower():
                return social_profile.url or ""

        return ""

    def _format_location(self, profile: CareerProfile) -> str:
        """
        Format location as "City, State" string.

        Returns:
            Formatted location string or empty string
        """
        if not profile.basics.location:
            return ""

        loc = profile.basics.location
        parts = []

        if loc.city:
            parts.append(loc.city)
        if loc.region:
            parts.append(loc.region)

        return ", ".join(parts)
