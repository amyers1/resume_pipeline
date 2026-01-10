"""
Resume draft generation with experience grouping.
"""

import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..models import JDRequirements, CareerProfile, Achievement
from ..config import PipelineConfig


class DraftGenerator:
    """Generates initial resume drafts with proper structure and grouping."""

    def __init__(self, llm: ChatOpenAI, config: PipelineConfig):
        self.llm = llm
        self.config = config
        self._setup_prompts()

    def _setup_prompts(self):
        """Initialize generation prompts."""
        self.system_prompt = """You are an expert ATS-optimized resume writer for senior defense/aerospace engineers.

CRITICAL RULES - ACCURACY AND TRUTH:
1. NEVER fabricate skills, tools, certifications, or experience not in the input data
2. NEVER invent metrics, dollar amounts, team sizes, or quantitative claims
3. NEVER add technologies or frameworks not explicitly present in achievements
4. Preserve ALL factual metrics exactly as provided
5. When rephrasing, maintain the substance and scope of original claims

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

EXPERIENCE GROUPING:
- Roles from 2014 onward: Full detailed entries with 4-6 bullets each
- Roles from 2006-2016: Group under "Other Relevant Experience" heading
- Grouped entries: Organization, Title, Location, Dates on one line, then 2-3 key bullets

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

Candidate profile:
{profile_json}

Top achievements for this role:
{achievements_json}

Contact info (header only):
Name: {name}
Email: {email}
Phone: {phone}
Location: {location}
LinkedIn: {linkedin}

IMPORTANT: Current year is {current_year}. Roles from 2014+ get detailed treatment (4-6 bullets).
Roles from 2006-2016 go under "Other Relevant Experience" with 2-3 bullets each.

Generate complete ATS-optimized resume in markdown. Target 2 pages maximum."""

    def generate(
        self,
        jd: JDRequirements,
        profile: CareerProfile,
        achievements: list[Achievement]
    ) -> str:
        """
        Generate resume draft.

        Args:
            jd: Job requirements
            profile: Career profile
            achievements: Matched achievements

        Returns:
            Resume draft in markdown format
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("user", self.user_prompt)
        ])

        chain = prompt | self.llm

        resp = chain.invoke({
            "jd_json": jd.model_dump_json(indent=2),
            "profile_json": profile.model_dump_json(indent=2),
            "achievements_json": json.dumps(
                [a.model_dump() for a in achievements], indent=2
            ),
            "name": profile.full_name,
            "email": profile.email or "",
            "phone": profile.phone or "",
            "location": profile.location or "",
            "linkedin": profile.linkedin or "",
            "current_year": self.config.current_year,
        })

        return resp.content if hasattr(resp, "content") else str(resp)
