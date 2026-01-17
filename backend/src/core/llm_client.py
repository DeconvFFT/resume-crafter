"""LLM client with Groq streaming and Chain-of-Thought support.

Provides structured outputs using Instructor with real-time streaming
of LLM reasoning for transparency and better UX.

Key features:
- Groq llama-3.3-70b-versatile as the primary model
- Streaming with Chain-of-Thought parsing
- Structured outputs via Instructor
- Callback support for real-time event publishing
"""

import asyncio
import logging
import re
from typing import AsyncIterator, Callable, TypeVar

import instructor
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import get_settings
from src.models.schemas.llm_outputs import (
    DocumentClassification,
    ExperienceExtractionResult,
    JobDescriptionExtraction,
    MatchRankingResult,
    ProjectExtractionResult,
    ProjectUnderstanding,
    ProjectEnrichmentResult,
    SkillExtractionResult,
    PublicationExtractionResult,
)

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T", bound=BaseModel)

# Callback type for streaming thinking events
ThinkingCallback = Callable[[str, bool], None]  # (thinking_text, is_complete)


def _create_llm_provider():
    """Create the LLM provider (Groq with llama-3.3-70b-versatile).

    Returns both sync and async clients for different use cases:
    - Sync client: Used with Instructor for structured outputs
    - Async client: Used for streaming with Chain-of-Thought
    """
    # Groq is the primary and recommended provider
    if settings.groq_api_key:
        logger.info(f"Using Groq cloud LLM with model: {settings.groq_model}")

        # Sync client for Instructor structured outputs
        sync_client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
        )
        instructor_client = instructor.from_openai(sync_client, mode=instructor.Mode.JSON)

        # Async client for streaming
        async_client = AsyncOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.groq_api_key,
        )

        return instructor_client, async_client, settings.groq_model

    # Fallback to OpenRouter if Groq not configured
    if settings.openrouter_api_key:
        logger.warning("Groq API key not set, falling back to OpenRouter")
        logger.info(f"Using OpenRouter cloud LLM with model: {settings.openrouter_model}")

        sync_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            default_headers={
                "HTTP-Referer": "https://resume-crafter.local",
                "X-Title": "Resume Crafter",
            },
        )
        instructor_client = instructor.from_openai(sync_client, mode=instructor.Mode.MD_JSON)

        async_client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.openrouter_api_key,
            default_headers={
                "HTTP-Referer": "https://resume-crafter.local",
                "X-Title": "Resume Crafter",
            },
        )

        return instructor_client, async_client, settings.openrouter_model

    # Last resort: Ollama (local)
    logger.warning("No cloud API keys set, falling back to Ollama (local)")
    logger.info(f"Using Ollama (local) with model: {settings.ollama_model}")

    sync_client = OpenAI(
        base_url=settings.ollama_base_url,
        api_key="ollama",
    )
    instructor_client = instructor.from_openai(sync_client, mode=instructor.Mode.JSON)

    async_client = AsyncOpenAI(
        base_url=settings.ollama_base_url,
        api_key="ollama",
    )

    return instructor_client, async_client, settings.ollama_model


# Chain-of-Thought prompt template
COT_SYSTEM_SUFFIX = """

IMPORTANT: Structure your response with your reasoning process visible:
1. First, wrap your thinking/reasoning in <thinking>...</thinking> tags
2. Then, provide your final structured answer

Example format:
<thinking>
Let me analyze this step by step...
[Your detailed reasoning here]
</thinking>

[Your structured JSON response here]"""


def _extract_thinking(text: str) -> tuple[str, str]:
    """Extract thinking section from response text.

    Args:
        text: Full response text.

    Returns:
        Tuple of (thinking_content, remaining_text).
    """
    thinking_match = re.search(r"<thinking>(.*?)</thinking>", text, re.DOTALL)
    if thinking_match:
        thinking = thinking_match.group(1).strip()
        remaining = text[thinking_match.end():].strip()
        return thinking, remaining
    return "", text


class LLMClient:
    """Client for interacting with LLM APIs using structured outputs and streaming.

    Primary provider: Groq with llama-3.3-70b-versatile
    Features:
    - Structured outputs via Instructor
    - Streaming with Chain-of-Thought extraction
    - Real-time thinking callbacks for UI updates
    """

    def __init__(self):
        """Initialize the LLM client with sync and async capabilities."""
        self._client, self._async_client, self._model = _create_llm_provider()
        self._provider = settings.llm_provider
        self._thinking_callback: ThinkingCallback | None = None

    def set_thinking_callback(self, callback: ThinkingCallback | None) -> None:
        """Set callback for streaming thinking events.

        Args:
            callback: Function that receives (thinking_text, is_complete).
        """
        self._thinking_callback = callback

    async def _stream_with_thinking(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
    ) -> str:
        """Stream LLM response with Chain-of-Thought extraction.

        Streams the response and calls the thinking callback for each chunk
        of reasoning. Returns the full response for further processing.

        Args:
            system_prompt: System message for context.
            user_prompt: User message with the actual request.
            max_tokens: Maximum tokens in response.

        Returns:
            Full response text.
        """
        # Add CoT instruction to system prompt
        enhanced_system = system_prompt + COT_SYSTEM_SUFFIX

        stream = await self._async_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": enhanced_system},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tokens,
            stream=True,
        )

        full_response = ""
        thinking_buffer = ""
        in_thinking = False
        thinking_emitted = False

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            if not delta.content:
                continue

            content = delta.content
            full_response += content

            # Stream thinking to callback
            if self._thinking_callback:
                # Detect thinking section
                if "<thinking>" in full_response and not in_thinking:
                    in_thinking = True
                    # Extract what we have so far in thinking
                    start_idx = full_response.find("<thinking>") + len("<thinking>")
                    thinking_buffer = full_response[start_idx:]

                if in_thinking:
                    if "</thinking>" in full_response:
                        # Thinking complete - extract and emit
                        if not thinking_emitted:
                            thinking, _ = _extract_thinking(full_response)
                            self._thinking_callback(thinking, True)
                            thinking_emitted = True
                        in_thinking = False
                    else:
                        # Stream incremental thinking
                        thinking_buffer += content
                        # Emit periodically for real-time feel
                        if len(content) > 0:
                            self._thinking_callback(content, False)

        return full_response

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    async def _create_completion(
        self,
        response_model: type[T],
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
    ) -> T:
        """Create a structured completion with retry logic.

        Args:
            response_model: Pydantic model for structured output.
            system_prompt: System message for context.
            user_prompt: User message with the actual request.
            max_tokens: Maximum tokens in response (default 8192 for complex extractions).

        Returns:
            Structured response matching the response_model.
        """
        try:
            logger.info(f"LLM request starting: model={self._model}, response_model={response_model.__name__}")
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_model=response_model,
                max_tokens=max_tokens,
            )
            logger.info(f"LLM request completed: {response_model.__name__}")
            return response
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

    async def classify_document(self, document_text: str) -> DocumentClassification:
        """Classify a document as resume, experience, project, or supporting.

        Args:
            document_text: Extracted text from the document.

        Returns:
            Classification result with confidence and reasoning.
        """
        system_prompt = """You are an expert document classifier for resume-building applications.
Your task is to classify documents into one of four categories:

1. RESUME: A full CV or resume that contains BOTH work experiences AND projects
   - Contains multiple sections: work history, projects, skills, education
   - Has both company names/job titles AND project names/technologies
   - This is the most common type when someone uploads their complete resume

2. EXPERIENCE: Work experience ONLY (no projects section)
   - Contains company names, job titles, employment dates
   - Describes responsibilities, achievements, roles
   - Does NOT contain a projects section

3. PROJECT: Personal or professional projects ONLY (no work experience)
   - Contains project names, descriptions, technologies used
   - May have GitHub links, demo URLs, technical details
   - Does NOT contain work experience/employment history

4. SUPPORTING: Supporting documents that enhance credentials
   - Research papers, publications
   - Certifications, credentials
   - Recommendation letters
   - Portfolio links, other evidence

IMPORTANT: If the document contains BOTH work experiences AND projects, classify it as "resume".
Think step by step:
1. First, look for work experience sections (job titles, company names, employment dates)
2. Then, look for project sections (project names, GitHub links, technologies)
3. If BOTH are present, classify as "resume"
4. If only work experience, classify as "experience"
5. If only projects, classify as "project"
6. If neither (or supporting docs), classify as "supporting"

Provide:
- Your classification
- A confidence score (0.0-1.0)
- Your detailed reasoning explaining what you found
- Whether the document has_experiences (true/false)
- Whether the document has_projects (true/false)
- Any entities you detected"""

        user_prompt = f"""Please classify the following document:

---
{document_text[:8000]}
---

Think through what sections and content you see, then provide your classification with confidence score and detailed reasoning."""

        return await self._create_completion(
            response_model=DocumentClassification,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def extract_experiences(self, document_text: str) -> ExperienceExtractionResult:
        """Extract structured experience data from a document.

        Args:
            document_text: Text from an experience document.

        Returns:
            Extracted experiences with bullets, skills, metrics.
        """
        system_prompt = """You are an expert resume parser. Extract ONLY work experience information from the document.

CRITICAL: Distinguish between WORK EXPERIENCES and PROJECTS:

WORK EXPERIENCES (extract these):
- Employment at a company/organization with a job title
- Has an employer name (company, startup, organization, agency)
- Has a job title/role (Software Engineer, Manager, Intern, etc.)
- Describes employment relationship (worked at, employed by, joined)
- Usually has employment dates

PROJECTS (DO NOT extract these as experiences):
- Personal projects, side projects, hobby projects
- Academic projects, course projects, thesis work
- Open source contributions
- Freelance projects without a clear employer
- Projects named with descriptive titles (e.g., "E-commerce Platform", "ML Pipeline")
- Entries with GitHub links, demo URLs
- Portfolio items

COMMON MISTAKES TO AVOID:
- DO NOT treat "Personal Portfolio Website" as work experience
- DO NOT treat "E-commerce Platform - Developer" as employment unless there's a clear company
- DO NOT extract entries from "Projects" sections as experiences
- DO NOT confuse project names for company names

For each VALID work experience, extract:
- Company name (must be a real organization, not a project name)
- Job title/role (must be an employment role)
- Location (if mentioned)
- Start date (YYYY-MM format)
- End date (YYYY-MM format, or null if current)
- Whether it's a current position
- Bullet points describing responsibilities and achievements

For each bullet point, identify:
- The core content
- Skills demonstrated (technical and soft skills)
- Quantified metrics (e.g., "increased sales by 50%", "managed team of 10")
- Action verbs used (e.g., "Led", "Developed", "Implemented")

Be thorough but accurate. Only extract ACTUAL EMPLOYMENT, not projects."""

        user_prompt = f"""Extract ONLY work experiences (employment) from this document.

IMPORTANT: Do NOT include personal projects, academic projects, or side projects.
Only extract entries that represent actual employment at a company/organization.

---
{document_text[:10000]}
---

Return structured data for each work experience found. If an entry looks like a project rather than employment, skip it."""

        return await self._create_completion(
            response_model=ExperienceExtractionResult,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def extract_projects(self, document_text: str) -> ProjectExtractionResult:
        """Extract structured project data from a document.

        Args:
            document_text: Text from a project document.

        Returns:
            Extracted projects with descriptions, technologies, links.
        """
        system_prompt = """You are an expert at parsing project documentation and portfolios.

For each project, extract:
- Project name
- Description (brief summary)
- Technologies used (programming languages, frameworks, tools)
- Start/end dates if mentioned
- Bullet points describing what was built/achieved
- Links (GitHub repository, live demo, documentation, video, paper)

CRITICAL FOR LINKS - READ CAREFULLY:
The document contains an "--- EXTRACTED HYPERLINKS ---" section at the end with the ACTUAL URLs from the document.
These are the real hyperlinks that were behind clickable text in the original PDF/DOCX.

You MUST:
1. Look at the "--- EXTRACTED HYPERLINKS ---" section to find real URLs
2. Match each project with its corresponding GitHub URL from that section
3. Use the FULL URL from the hyperlinks section (e.g., https://github.com/username/repo-name)
4. DO NOT use display text or project names as URLs - only use actual https:// URLs from the hyperlinks section

For example, if the document shows "Project Name: Fetch and Slide" and the hyperlinks section contains:
  - https://github.com/DeconvFFT/fetch-and-slide-HRE-PRE
Then use that full GitHub URL for the project.

LINK VALIDATION:
- Only use REAL, COMPLETE URLs that start with https:// or http://
- GitHub links MUST be in format: https://github.com/username/repo
- Do NOT include localhost URLs, placeholder URLs, or incomplete URLs
- If no matching valid URL is found in the hyperlinks section, leave links array empty
- Each link should have "url" (the full URL) and "type" (github/demo/docs/video/paper/other)

For each bullet point, identify:
- The core achievement or feature
- Skills/technologies demonstrated
- Any metrics or quantified results

Extract all distinct projects mentioned."""

        # Ensure the hyperlinks section is always included
        # It's at the end of the document and critical for extracting correct URLs
        hyperlinks_marker = "--- EXTRACTED HYPERLINKS ---"
        github_urls = []
        if hyperlinks_marker in document_text:
            # Split to get main content and hyperlinks section
            main_content = document_text[:document_text.find(hyperlinks_marker)]
            hyperlinks_section = document_text[document_text.find(hyperlinks_marker):]
            # Truncate main content but always include full hyperlinks section
            truncated_main = main_content[:8000] if len(main_content) > 8000 else main_content
            doc_for_prompt = truncated_main + "\n\n" + hyperlinks_section

            # Extract GitHub URLs for post-processing
            github_urls = re.findall(r'https://github\.com/[^\s\]]+', hyperlinks_section)
            github_urls = [url.rstrip('.,;:!?)>]') for url in github_urls]
        else:
            doc_for_prompt = document_text[:10000]

        user_prompt = f"""Extract all projects from this document:

---
{doc_for_prompt}
---

IMPORTANT: Look at the "--- EXTRACTED HYPERLINKS ---" section at the end to find the REAL GitHub URLs for each project.
Match projects to their GitHub links using the repository names in the URLs.

Return structured data for each project found."""

        result = await self._create_completion(
            response_model=ProjectExtractionResult,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Post-process: Match projects to GitHub URLs from hyperlinks section
        if github_urls and result and result.projects:
            result = self._match_projects_to_github_urls(result, github_urls)

        return result

    def _match_projects_to_github_urls(
        self,
        result: ProjectExtractionResult,
        github_urls: list[str]
    ) -> ProjectExtractionResult:
        """Match extracted projects to actual GitHub URLs from hyperlinks section.

        Uses multiple matching strategies:
        1. Fuzzy matching between project names and GitHub repo names
        2. Order-based matching (if same number of projects and links)
        3. Removes hallucinated URLs not in the hyperlinks section
        """
        def normalize(text: str) -> str:
            """Normalize text for matching: lowercase, remove special chars."""
            return re.sub(r'[^a-z0-9]', '', text.lower())

        def get_word_stems(text: str) -> set[str]:
            """Get word stems for matching (e.g., sliding -> slid)."""
            words = re.sub(r'[^a-z\s]', '', text.lower()).split()
            stems = set()
            for word in words:
                if len(word) >= 4:
                    stems.add(word)
                    # Add common stem variations
                    if word.endswith('ing'):
                        stems.add(word[:-3])  # sliding -> slid
                        stems.add(word[:-3] + 'e')  # sliding -> slide
                    if word.endswith('ed'):
                        stems.add(word[:-2])  # fetched -> fetch
                    if word.endswith('s') and len(word) > 4:
                        stems.add(word[:-1])  # objects -> object
            return stems

        def extract_repo_name(url: str) -> str | None:
            """Extract repository name from GitHub URL.

            Returns None if URL is not a valid repo URL (e.g., just a user page).
            """
            # https://github.com/user/repo-name -> repo-name
            # URL should have format: https://github.com/user/repo
            # Split: ['https:', '', 'github.com', 'user', 'repo']
            parts = url.rstrip('/').split('/')
            # Must have at least 5 parts to be a valid repo URL
            if len(parts) >= 5 and parts[2] == 'github.com':
                return parts[4]  # The repo name
            return None  # Not a valid repo URL

        # Track which URLs have been assigned
        used_urls = set()

        for project in result.projects:
            project_name_normalized = normalize(project.name)
            project_stems = get_word_stems(project.name)

            # Try to find a matching GitHub URL from the REAL extracted hyperlinks
            # ALWAYS prefer hyperlinks over LLM-generated URLs (LLM often hallucinates)
            best_match = None
            best_score = 0

            for github_url in github_urls:
                if github_url in used_urls:
                    continue  # Already assigned to another project

                repo_name = extract_repo_name(github_url)
                if not repo_name:
                    continue  # Skip invalid URLs (user pages, etc.)

                repo_name_normalized = normalize(repo_name)
                repo_stems = get_word_stems(repo_name.replace('-', ' ').replace('_', ' '))

                if not repo_name_normalized:
                    continue

                score = 0

                # Check for substring match in either direction
                if project_name_normalized and project_name_normalized in repo_name_normalized:
                    score = max(score, len(project_name_normalized) / len(repo_name_normalized))
                elif repo_name_normalized in project_name_normalized:
                    score = max(score, len(repo_name_normalized) / len(project_name_normalized) if project_name_normalized else 0)

                # Check individual words from project name (at least 4 chars)
                project_words = [normalize(w) for w in project.name.split() if len(w) > 2]
                for word in project_words:
                    if len(word) >= 4 and word in repo_name_normalized:
                        score = max(score, len(word) / len(repo_name_normalized))

                # Check stem matching (e.g., "sliding" matches "slide")
                # Method 1: Set intersection
                common_stems = project_stems & repo_stems
                if common_stems:
                    stem_score = len(common_stems) / max(len(project_stems), 1) * 0.8
                    score = max(score, stem_score)

                # Method 2: Check if project stems appear in the normalized repo name
                for stem in project_stems:
                    if len(stem) >= 4 and stem in repo_name_normalized:
                        stem_score = len(stem) / len(repo_name_normalized)
                        if stem_score > score:
                            score = stem_score
                            logger.debug(f"Stem '{stem}' found in repo '{repo_name}' (score: {stem_score:.2f})")

                if score > best_score:
                    best_score = score
                    best_match = github_url

            # If we found a match from hyperlinks, REPLACE any LLM-generated github links
            if best_match and best_score > 0.15:  # Low threshold - prefer real URLs
                # Remove ALL github links (LLM-generated ones are likely hallucinated)
                project.links = [
                    link for link in project.links
                    if link.get("type") != "github"
                ]
                # Add the REAL URL from hyperlinks
                project.links.append({
                    "url": best_match,
                    "type": "github"
                })
                used_urls.add(best_match)
                logger.info(f"Matched project '{project.name}' to GitHub URL: {best_match} (score: {best_score:.2f})")
            else:
                # No match found - remove any github links since they're likely hallucinated
                llm_github_links = [l for l in project.links if l.get("type") == "github"]
                if llm_github_links:
                    llm_url = llm_github_links[0].get("url", "")
                    if llm_url not in github_urls:
                        # LLM hallucinated this URL - remove it
                        project.links = [l for l in project.links if l.get("type") != "github"]
                        logger.warning(f"Removed hallucinated GitHub URL for project '{project.name}': {llm_url}")

        # Fallback: Order-based matching for unassigned projects
        # If we have unassigned projects and unused GitHub URLs, match by order
        unassigned_projects = [
            p for p in result.projects
            if not any(l.get("type") == "github" for l in p.links)
        ]
        unused_github_urls = [u for u in github_urls if u not in used_urls]

        if unassigned_projects and unused_github_urls:
            logger.info(f"Order-based fallback: {len(unassigned_projects)} projects, {len(unused_github_urls)} URLs")
            for project, github_url in zip(unassigned_projects, unused_github_urls):
                project.links.append({
                    "url": github_url,
                    "type": "github"
                })
                logger.info(f"Order-matched project '{project.name}' to GitHub URL: {github_url}")

        return result

    async def extract_skills(self, document_text: str) -> SkillExtractionResult:
        """Extract skills from any document.

        Args:
            document_text: Raw text of the document.

        Returns:
            Extracted skills with categories and proficiency levels.
        """

        system_prompt = """You are an expert at identifying technical and professional skills from documents.

Extract ALL skills mentioned in the document, including:
- Programming languages (Python, JavaScript, Java, etc.)
- Frameworks and libraries (React, Django, TensorFlow, etc.)
- Databases (PostgreSQL, MongoDB, Redis, etc.)
- Cloud platforms (AWS, GCP, Azure)
- DevOps tools (Docker, Kubernetes, CI/CD)
- Other tools (Git, Jira, Figma, etc.)
- Soft skills (Leadership, Communication, etc.)
- Methodologies (Agile, Scrum, TDD, etc.)

For each skill:
- Categorize it appropriately
- Estimate proficiency if context suggests it (beginner, intermediate, advanced, expert)
- Note years of experience if mentioned
- Include context where the skill was mentioned

Be thorough - extract even skills that are only mentioned once.
Do NOT make up skills that aren't in the document."""

        user_prompt = f"""Extract all skills from this document:

---
{document_text[:15000]}
---

Return every skill mentioned with appropriate categorization."""

        return await self._create_completion(
            response_model=SkillExtractionResult,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def extract_publications(self, document_text: str) -> PublicationExtractionResult:
        """Extract publications from any document.

        Args:
            document_text: Raw text of the document.

        Returns:
            Extracted publications with details.
        """

        system_prompt = """You are an expert at identifying academic and professional publications from documents.

Extract ALL publications mentioned, including:
- Journal articles
- Conference papers
- Books or book chapters
- Theses and dissertations
- Patents
- Preprints (arXiv, etc.)

For each publication, extract:
- Full title
- Authors (as a list)
- Publication type
- Venue (journal, conference, publisher)
- Publication date (YYYY or YYYY-MM format)
- DOI if mentioned
- URL if available
- Brief abstract or description if available
- Whether the document owner is first author

Be thorough but only extract actual publications mentioned in the document.
Do NOT make up publications that aren't in the document."""

        user_prompt = f"""Extract all publications from this document:

---
{document_text[:15000]}
---

Return every publication mentioned with full details."""

        return await self._create_completion(
            response_model=PublicationExtractionResult,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def extract_job_requirements(self, job_text: str) -> JobDescriptionExtraction:
        """Extract structured requirements from a job description.

        Args:
            job_text: Text of the job description.

        Returns:
            Extracted job details and requirements.
        """
        system_prompt = """You are an expert job description analyzer. Your task is to extract ALL requirements from job postings.

CRITICAL: You MUST extract requirements. Even minimal job descriptions have requirements.

Extract the following from the job posting:
- Company name (look for company mentions, "About Us", headers)
- Job title/role (the position being advertised)
- Location (including remote options, city/state/country)
- Salary range (if mentioned, any format)
- Experience level: entry (0-1 years), junior (1-3), mid (3-5), senior (5-8), lead (8+), principal (10+)

REQUIREMENT EXTRACTION - BE THOROUGH:
Look for requirements in:
- "Requirements", "Qualifications", "What we're looking for" sections
- "Responsibilities" (implies required skills)
- "Nice to have", "Preferred", "Bonus" sections
- Job title itself (e.g., "Senior Python Developer" = Python, senior experience)
- Company/industry context (e.g., fintech = financial domain knowledge)

Categorize each requirement as:
- skill: Technical skills, programming languages, tools, frameworks, platforms
- experience: Years of experience, domain expertise, industry background
- education: Degrees, educational requirements
- certification: Specific certifications (AWS, PMP, CPA, etc.)
- soft_skill: Communication, leadership, teamwork, problem-solving
- other: Anything else (clearance, location requirements, etc.)

Rate importance 1-5:
- 5: "Must have", "Required", "Essential", explicitly mandatory
- 4: Strongly preferred, emphasized multiple times, key responsibilities
- 3: Listed requirement, standard importance
- 2: "Nice to have", "Preferred", "Bonus", "Plus"
- 1: Mentioned but not emphasized

IMPORTANT: Extract at least 3-5 requirements from any job description. If the posting is vague, infer requirements from:
- The job title (what skills does this role typically need?)
- The responsibilities listed
- The industry/company context

Extract keywords for each requirement to aid matching."""

        user_prompt = f"""Analyze this job description and extract ALL requirements.

IMPORTANT: You must return at least several requirements. Look carefully at the entire text.

---
{job_text[:12000]}
---

Return structured job details with company, role, and a comprehensive list of categorized requirements."""

        return await self._create_completion(
            response_model=JobDescriptionExtraction,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def rank_matches(
        self,
        requirement: str,
        candidate_bullets: list[dict],
    ) -> MatchRankingResult:
        """Re-rank candidate bullets for a job requirement using LLM.

        Args:
            requirement: The job requirement text.
            candidate_bullets: List of candidate bullets with id and content.

        Returns:
            Ranked bullets with scores and explanations.
        """
        system_prompt = """You are an expert resume-to-job matcher.

Given a job requirement and candidate resume bullets, rank the bullets by relevance.

Consider:
- Direct skill/experience match
- Transferable skills
- Quantified achievements that demonstrate capability
- Context and scope similarity

For each bullet, provide:
- Relevance score (0.0-1.0)
- Brief explanation of why it matches (or doesn't)
- Matching skills identified
- Any gaps (requirement aspects not addressed)

Rank from most to least relevant."""

        bullets_text = "\n".join(
            f"[{b['id']}] {b['content']}" for b in candidate_bullets
        )

        user_prompt = f"""Job Requirement:
{requirement}

Candidate Bullets:
{bullets_text}

Rank these bullets by relevance to the requirement."""

        return await self._create_completion(
            response_model=MatchRankingResult,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def understand_github_project(
        self,
        repo_info: dict,
    ) -> ProjectUnderstanding:
        """Analyze a GitHub repository and build understanding of the project.

        This is Agent 2 in the enrichment pipeline - it takes raw GitHub data
        and extracts meaningful understanding about what the project does,
        its architecture, and its impact.

        Args:
            repo_info: Dictionary containing GitHub repository information.

        Returns:
            ProjectUnderstanding with analyzed project details.
        """
        system_prompt = """You are an expert software engineer and technical analyst.
Your task is to analyze a GitHub repository and build a deep understanding of the project.

Focus on extracting:
1. What the project does and what problem it solves
2. Key technical features and capabilities
3. The technologies and architecture used
4. Indicators of project quality and impact (stars, forks, contributors, commits)
5. What makes this project unique or impressive
6. Who would benefit from this project

Be thorough but concise. Look for evidence of real-world impact, technical sophistication,
and professional quality. Consider code quality signals like:
- Number of contributors (team collaboration)
- Stars and forks (community interest)
- Commit count (active development)
- Documentation (README quality)
- Topics and proper categorization

Rate the complexity level honestly based on the technical challenges involved."""

        # Format repo info for the prompt
        repo_summary = f"""
Repository: {repo_info.get('full_name', 'Unknown')}
Description: {repo_info.get('description', 'No description')}
Primary Language: {repo_info.get('language', 'Unknown')}
Languages Used: {', '.join(repo_info.get('languages', {}).keys()) or 'Unknown'}
Topics: {', '.join(repo_info.get('topics', [])) or 'None'}

Metrics:
- Stars: {repo_info.get('stars', 0)}
- Forks: {repo_info.get('forks', 0)}
- Watchers: {repo_info.get('watchers', 0)}
- Contributors: {repo_info.get('contributors_count', 0)}
- Commits: {repo_info.get('commits_count', 0)}
- Open Issues: {repo_info.get('open_issues', 0)}

Created: {repo_info.get('created_at', 'Unknown')}
Last Updated: {repo_info.get('updated_at', 'Unknown')}
Last Pushed: {repo_info.get('pushed_at', 'Unknown')}

License: {repo_info.get('license', 'Not specified')}
Homepage: {repo_info.get('homepage', 'None')}
Has Wiki: {repo_info.get('has_wiki', False)}
Has Pages: {repo_info.get('has_pages', False)}
"""

        readme_content = repo_info.get('readme_content', '')
        if readme_content:
            # Truncate README if too long
            readme_preview = readme_content[:6000] if len(readme_content) > 6000 else readme_content
            repo_summary += f"\n\nREADME Content:\n{readme_preview}"

        user_prompt = f"""Analyze this GitHub repository and extract a comprehensive understanding:

{repo_summary}

Provide detailed analysis of the project's purpose, features, architecture, and impact."""

        return await self._create_completion(
            response_model=ProjectUnderstanding,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def generate_project_bullets(
        self,
        project_understanding: ProjectUnderstanding,
        existing_description: str | None = None,
    ) -> ProjectEnrichmentResult:
        """Generate resume-ready bullet points from project understanding.

        This is Agent 3 in the enrichment pipeline - it takes the project
        understanding and converts it into impactful resume bullets.

        Args:
            project_understanding: Analyzed project understanding.
            existing_description: Optional existing project description from user.

        Returns:
            ProjectEnrichmentResult with enriched bullets.
        """
        system_prompt = """You are an expert resume writer specializing in technical roles.
Your task is to convert project understanding into powerful, resume-ready bullet points.

RULES FOR WRITING EXCELLENT RESUME BULLETS:
1. Start each bullet with a STRONG ACTION VERB (Built, Developed, Implemented, Designed, etc.)
2. Include QUANTIFIABLE METRICS when possible (users, performance improvements, lines of code, etc.)
3. Highlight TECHNICAL SKILLS and technologies used
4. Show IMPACT - what was the benefit or result?
5. Be SPECIFIC - avoid vague statements
6. Keep each bullet to 1-2 lines maximum
7. Order bullets from MOST IMPACTFUL to least impactful

EXAMPLE GOOD BULLETS:
- "Developed a real-time data processing pipeline handling 1M+ events/day using Apache Kafka and Python"
- "Built a responsive web application using React and TypeScript, achieving 95% Lighthouse performance score"
- "Implemented CI/CD pipeline with GitHub Actions, reducing deployment time from 2 hours to 15 minutes"
- "Designed and deployed microservices architecture on AWS, improving system reliability to 99.9% uptime"

AVOID:
- Vague statements like "Worked on backend systems"
- Starting with weak verbs like "Helped", "Assisted", "Was responsible for"
- Missing impact or metrics
- Overly technical jargon without context

Generate 3-8 high-quality bullet points, prioritized by impact and relevance for a resume."""

        understanding_summary = f"""
Project Type: {project_understanding.project_type}
Primary Purpose: {project_understanding.primary_purpose}
Complexity Level: {project_understanding.complexity_level}

Key Features:
{chr(10).join(f"- {f}" for f in project_understanding.key_features)}

Technologies Used: {', '.join(project_understanding.technologies_used)}

Technical Architecture: {project_understanding.technical_architecture or 'Not specified'}

Target Users: {project_understanding.target_users or 'Not specified'}

Unique Aspects:
{chr(10).join(f"- {a}" for a in project_understanding.unique_aspects)}

Scale Indicators: {project_understanding.scale_indicators}
"""

        user_prompt = f"""Generate resume-ready bullet points for this project:

{understanding_summary}
"""
        if existing_description:
            user_prompt += f"\nUser's Original Description: {existing_description}\n"

        user_prompt += """
Create 3-8 impactful bullet points that would impress a hiring manager.
For each bullet, identify the skills demonstrated and rate its strength."""

        return await self._create_completion(
            response_model=ProjectEnrichmentResult,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )


# Singleton instance
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Get or create the LLM client singleton."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
