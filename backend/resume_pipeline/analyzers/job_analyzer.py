"""
Job description analysis and requirement extraction.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from ..models import JDRequirements


class JobAnalyzer:
    """Analyzes job descriptions and extracts structured requirements."""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._setup_prompts()

    def _setup_prompts(self):
        """Initialize LLM prompts."""
        self.refine_prompt = ChatPromptTemplate.from_messages([
            ("system",
             "You extract and structure job requirements for resume tailoring. "
             "Rewrite responsibilities as 5-10 concise, scannable bullets. "
             "Refine domain_focus and keywords to capture essential terms. "
             "Preserve all factual content. Be thorough but concise."),
            ("user",
             "Job requirements JSON:\n{jd_json}\n\n"
             "Return refined JSON with improved responsibilities, domain_focus, and keywords.")
        ])

    def analyze(self, jd_json: dict) -> JDRequirements:
        """
        Analyze job description and return structured requirements.

        Args:
            jd_json: Raw job description JSON

        Returns:
            Structured JDRequirements object
        """
        # Initial parsing
        jd_req = self._parse_job_json(jd_json)

        # Refine with LLM
        refined = self._refine_requirements(jd_req)

        return refined

    def _parse_job_json(self, jd_json: dict) -> JDRequirements:
        """Map raw job JSON to structured requirements."""
        job_details = jd_json.get("job_details", {})
        job_desc = jd_json.get("job_description", {})

        role_title = job_details.get("job_title") or job_desc.get("headline") or "Unknown"
        location = job_details.get("location_detail") or job_details.get("location")
        clearance = job_details.get("security_clearance_required")

        musts = job_desc.get("must_have_skills", []) or []
        nices = job_desc.get("nice_to_have_skills", []) or []

        # Infer seniority
        seniority = "Senior" if any(x in role_title for x in ["Senior", "Sr", "Lead", "Principal"]) else "IC"

        # Extract responsibilities
        responsibilities = []
        if short_summary := job_desc.get("short_summary"):
            responsibilities.append(short_summary)

        # Extract domain focus from full text
        fulltext = (job_desc.get("full_text", "") or "").lower()
        domain_focus = self._extract_domains(fulltext)

        # Combine keywords
        keywords = sorted(set(musts + nices + role_title.split()))

        return JDRequirements(
            role_title=role_title,
            seniority=seniority,
            location=location,
            must_have_skills=musts,
            nice_to_have_skills=nices,
            responsibilities=responsibilities,
            clearance_or_eligibility=clearance,
            domain_focus=domain_focus,
            keywords=keywords,
        )

    def _extract_domains(self, fulltext: str) -> list[str]:
        """Extract technical domains from job description text."""
        domain_keywords = {
            "Electronic Warfare": ["electronic warfare", "ew"],
            "GPS": ["gps", "positioning"],
            "ISR": ["isr", "intelligence", "surveillance", "reconnaissance"],
            "Systems Engineering": ["systems engineer", "systems engineering"],
            "DoD Acquisition": ["acquisition", "dod acquisition"],
            "Cybersecurity": ["cyber", "security"],
        }

        domains = []
        for domain, keywords in domain_keywords.items():
            if any(kw in fulltext for kw in keywords):
                domains.append(domain)

        return domains

    def _refine_requirements(self, jd_req: JDRequirements) -> JDRequirements:
        """Use LLM to refine and enhance requirements."""
        chain = self.refine_prompt | self.llm.with_structured_output(JDRequirements)
        refined = chain.invoke({"jd_json": jd_req.model_dump_json()})
        return refined
