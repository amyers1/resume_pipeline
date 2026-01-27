"""
Job description analysis and requirement extraction.

Updated for Python 3.14 compatibility.
"""

from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from ..models import JDRequirements


class JobAnalyzer:
    """Analyzes job descriptions and extracts structured requirements."""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self._setup_prompts()

    def _setup_prompts(self) -> None:
        self.refine_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You extract and structure job requirements for resume tailoring. "
                    "Rewrite responsibilities as 5-10 concise, scannable bullets. "
                    "Refine domain_focus and keywords to capture essential terms. "
                    "Preserve all factual content. Be thorough but concise.",
                ),
                (
                    "user",
                    "Job requirements JSON:\n{jd_json}\n\n"
                    "Return refined JSON with improved responsibilities, domain_focus, and keywords.",
                ),
            ]
        )

    def analyze(self, jd_json: dict[str, Any]) -> JDRequirements:
        """
        Analyze job description and return structured requirements.

        Args:
            jd_json: Raw job description JSON from database or file

        Returns:
            Structured JDRequirements object with extracted information
        """
        # Initial parsing from raw JSON
        jd_req = self._parse_job_json(jd_json)

        # Refine with LLM to improve structure and extract keywords
        refined = self._refine_requirements(jd_req)

        return refined

    def _parse_job_json(self, jd_json: dict[str, Any]) -> JDRequirements:
        """
        Map raw job JSON to structured requirements.

        Handles both legacy file format and new PostgreSQL backend format.
        """
        # Extract nested job_details if present (legacy format)
        details = jd_json.get("job_details", jd_json)
        description = jd_json.get("job_description", {})

        # Build JDRequirements
        return JDRequirements(
            role_title=details.get("job_title", "Unknown Role"),
            company=details.get("company", "Unknown Company"),
            location=details.get("location"),
            seniority_level=self._infer_seniority(details.get("job_title", "")),
            domain_focus=self._extract_domains(description.get("full_text", "")),
            must_have_skills=description.get("must_have_skills", []),
            nice_to_have_skills=description.get("nice_to_have_skills", []),
            required_experience_years=description.get("required_experience_years_min"),
            required_education=description.get("required_education"),
            key_responsibilities=self._extract_responsibilities(
                description.get("full_text", "")
            ),
            keywords=self._extract_keywords(description),
        )

    def _refine_requirements(self, jd_req: JDRequirements) -> JDRequirements:
        """
        Use LLM to refine and improve structured requirements.

        The LLM helps with:
        - Better keyword extraction
        - Cleaner responsibility bullets
        - Domain identification
        """
        chain = self.refine_prompt | self.llm

        # Convert to JSON for LLM
        jd_json = jd_req.model_dump_json(indent=2)

        # Get refined version
        response = chain.invoke({"jd_json": jd_json})

        # Parse LLM response
        try:
            refined_data = self._parse_llm_response(response.content)
            return JDRequirements.model_validate(refined_data)
        except Exception as e:
            # If LLM response is malformed, return original
            print(f"  ⚠ LLM refinement failed: {e}, using original requirements")
            return jd_req

    def _extract_domains(self, full_text: str) -> list[str]:
        """
        Extract technical domains from job description text.

        Returns:
            List of domain keywords matching the expanded taxonomy used in achievement matching.
        """
        domains = []

        # Expanded domain keywords - aligned with achievement_matcher.py taxonomy
        domain_keywords = {
            # Core Technical Domains
            "EW": [
                "electronic warfare",
                "ew ",
                "jamming",
                "countermeasures",
                "threat library",
                "reprogramming",
            ],
            "ISR": [
                "isr",
                "intelligence",
                "surveillance",
                "reconnaissance",
                "sigint",
                "collection",
                "geoint",
            ],
            "RF": [
                "rf ",
                "radio frequency",
                "antenna",
                "electromagnetic",
                "signal processing",
                "spectrum",
            ],
            "Radar": ["radar", "synthetic aperture", "sar ", "aesa", "phased array"],
            "Cyber": [
                "cyber",
                "cybersecurity",
                "infosec",
                "penetration",
                "rmf",
                "ato",
                "vulnerability",
            ],
            "PNT": ["pnt", "gps", "navigation", "positioning", "timing", "gnss"],
            "Satellite_Ops": [
                "satellite",
                "spacecraft",
                "on-orbit",
                "launch",
                "space systems",
                "ground segment",
            ],
            "C2": ["command and control", "c2 ", "c4isr", "battle management"],
            # Engineering & Development
            "Systems_Engineering": [
                "systems engineer",
                "requirements",
                "integration",
                "verification",
                "mbse",
            ],
            "Electrical_Engineering": [
                "electrical engineer",
                "circuit",
                "power systems",
                "pcb",
                "asic",
            ],
            "Software_Dev": [
                "software",
                "developer",
                "programming",
                "python",
                "java",
                "c++",
                "code",
            ],
            "Data_Science": [
                "data science",
                "analytics",
                "machine learning",
                "ai ",
                "ml ",
                "deep learning",
                "neural",
            ],
            "Test_Eval": [
                "test",
                "evaluation",
                "t&e",
                "verification",
                "validation",
                "hitl",
                "qualification",
            ],
            "R&D": [
                "research",
                "r&d",
                "laboratory",
                "prototype",
                "technology development",
            ],
            # Leadership & Management
            "Program_Mgmt": [
                "program manag",
                "project manag",
                "portfolio",
                "acquisition",
                "budget",
                "schedule",
            ],
            "Technical_Leadership": [
                "technical lead",
                "chief engineer",
                "architect",
                "principal engineer",
            ],
            "Executive_Leadership": ["director", "vice president", "vp ", "executive"],
            # Operations
            "Operations": [
                "operations",
                "mission",
                "deployment",
                "operational",
                "sustainment",
            ],
            "Flight_Test": [
                "flight test",
                "developmental test",
                "airborne",
                "airworthiness",
            ],
            # Industries
            "Defense": [
                "defense",
                "military",
                "dod",
                "clearance",
                "classified",
                "air force",
                "army",
                "navy",
            ],
            "Aerospace": [
                "aerospace",
                "aircraft",
                "aviation",
                "lockheed",
                "northrop",
                "raytheon",
                "boeing",
                "l3harris",
            ],
            # Technologies
            "Cloud": [
                "cloud",
                "aws",
                "azure",
                "gcp",
                "devops",
                "kubernetes",
                "containerization",
            ],
            "Automation": ["automation", "automated", "scripting", "ci/cd", "pipeline"],
            "Sensors": ["sensor", "detector", "imaging", "electro-optical", "infrared"],
            "UAS": ["uas", "uav", "drone", "unmanned", "autonomous"],
        }

        text_lower = full_text.lower()
        for domain, keywords in domain_keywords.items():
            if any(kw in text_lower for kw in keywords):
                domains.append(domain)

        return domains

    def _extract_responsibilities(self, full_text: str) -> list[str]:
        """
        Extract key responsibilities from job description.

        Returns:
            List of responsibility bullets
        """
        # This is a placeholder - in production, would use NLP
        # For now, return empty and let LLM handle it in refinement
        return []

    def _extract_keywords(self, description: dict[str, Any]) -> list[str]:
        """
        Extract important keywords from job description.

        Combines must-have skills with additional keywords from text.
        """
        keywords = set()

        # Add must-have skills
        must_haves = description.get("must_have_skills", [])
        keywords.update(must_haves)

        # Add nice-to-have skills
        nice_to_haves = description.get("nice_to_have_skills", [])
        keywords.update(nice_to_haves)

        # Could add more sophisticated keyword extraction here

        return list(keywords)

    def _infer_seniority(self, job_title: str) -> str | None:
        """
        Infer seniority level from job title.

        Returns:
            One of: "entry", "mid", "senior", "lead", "principal", or None
        """
        title_lower = job_title.lower()

        seniority_keywords = {
            "principal": ["principal", "distinguished"],
            "lead": ["lead", "staff", "architect"],
            "senior": ["senior", "sr"],
            "mid": ["mid-level", "intermediate"],
            "entry": ["entry", "junior", "jr", "associate"],
        }

        for level, keywords in seniority_keywords.items():
            if any(kw in title_lower for kw in keywords):
                return level

        return None

    def _parse_llm_response(self, content: str) -> dict[str, Any]:
        """
        Parse LLM response into dictionary.

        Handles both JSON and markdown-wrapped JSON responses.
        """
        import json
        import re

        # Remove markdown code fences if present
        content = re.sub(r"```json\s*", "", content)
        content = re.sub(r"```\s*$", "", content)
        content = re.sub(r"```\s*$", "", content)
        content = content.strip()

        return json.loads(content)
