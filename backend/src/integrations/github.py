"""GitHub API integration for project enrichment."""

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class GitHubRepoInfo:
    """Information about a GitHub repository."""

    owner: str
    repo: str
    full_name: str
    description: str | None
    language: str | None
    languages: dict[str, int] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    stars: int = 0
    forks: int = 0
    watchers: int = 0
    open_issues: int = 0
    created_at: str | None = None
    updated_at: str | None = None
    pushed_at: str | None = None
    homepage: str | None = None
    license: str | None = None
    readme_content: str | None = None
    contributors_count: int = 0
    commits_count: int = 0
    has_wiki: bool = False
    has_pages: bool = False


class GitHubService:
    """Service for interacting with GitHub API."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        """Initialize GitHub service.

        Args:
            token: Optional GitHub personal access token for higher rate limits.
        """
        self.token = token
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "Resume-Crafter/1.0",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @staticmethod
    def parse_github_url(url: str) -> tuple[str, str] | None:
        """Parse a GitHub URL to extract owner and repo.

        Args:
            url: GitHub URL (e.g., https://github.com/owner/repo)

        Returns:
            Tuple of (owner, repo) or None if invalid.
        """
        import re

        patterns = [
            r"github\.com/([^/]+)/([^/\?#]+)",
            r"github\.com:([^/]+)/([^/\?#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner, repo = match.groups()
                # Remove .git suffix if present (use removesuffix, not rstrip!)
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return owner, repo

        return None

    async def fetch_repo_info(self, owner: str, repo: str) -> GitHubRepoInfo:
        """Fetch comprehensive information about a GitHub repository.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            GitHubRepoInfo with repository details.
        """
        client = await self._get_client()

        # Fetch main repo info
        response = await client.get(f"/repos/{owner}/{repo}")
        response.raise_for_status()
        data = response.json()

        repo_info = GitHubRepoInfo(
            owner=owner,
            repo=repo,
            full_name=data.get("full_name", f"{owner}/{repo}"),
            description=data.get("description"),
            language=data.get("language"),
            stars=data.get("stargazers_count", 0),
            forks=data.get("forks_count", 0),
            watchers=data.get("watchers_count", 0),
            open_issues=data.get("open_issues_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            pushed_at=data.get("pushed_at"),
            homepage=data.get("homepage"),
            license=data.get("license", {}).get("name") if data.get("license") else None,
            topics=data.get("topics", []),
            has_wiki=data.get("has_wiki", False),
            has_pages=data.get("has_pages", False),
        )

        # Fetch languages
        try:
            lang_response = await client.get(f"/repos/{owner}/{repo}/languages")
            if lang_response.status_code == 200:
                repo_info.languages = lang_response.json()
        except Exception as e:
            logger.warning(f"Failed to fetch languages for {owner}/{repo}: {e}")

        # Fetch contributor count
        try:
            contrib_response = await client.get(
                f"/repos/{owner}/{repo}/contributors",
                params={"per_page": 1, "anon": "1"},
            )
            if contrib_response.status_code == 200:
                # Get count from Link header
                link_header = contrib_response.headers.get("Link", "")
                if 'rel="last"' in link_header:
                    import re
                    match = re.search(r"page=(\d+)>; rel=\"last\"", link_header)
                    if match:
                        repo_info.contributors_count = int(match.group(1))
                else:
                    repo_info.contributors_count = len(contrib_response.json())
        except Exception as e:
            logger.warning(f"Failed to fetch contributors for {owner}/{repo}: {e}")

        # Fetch commit count (approximate from default branch)
        try:
            commits_response = await client.get(
                f"/repos/{owner}/{repo}/commits",
                params={"per_page": 1},
            )
            if commits_response.status_code == 200:
                link_header = commits_response.headers.get("Link", "")
                if 'rel="last"' in link_header:
                    import re
                    match = re.search(r"page=(\d+)>; rel=\"last\"", link_header)
                    if match:
                        repo_info.commits_count = int(match.group(1))
        except Exception as e:
            logger.warning(f"Failed to fetch commit count for {owner}/{repo}: {e}")

        # Fetch README content
        try:
            readme_response = await client.get(f"/repos/{owner}/{repo}/readme")
            if readme_response.status_code == 200:
                readme_data = readme_response.json()
                # Decode base64 content
                import base64
                content_b64 = readme_data.get("content", "")
                repo_info.readme_content = base64.b64decode(content_b64).decode("utf-8")
        except Exception as e:
            logger.warning(f"Failed to fetch README for {owner}/{repo}: {e}")

        return repo_info

    async def fetch_repo_from_url(self, url: str) -> GitHubRepoInfo | None:
        """Fetch repository information from a GitHub URL.

        Args:
            url: GitHub repository URL.

        Returns:
            GitHubRepoInfo or None if URL is invalid.
        """
        parsed = self.parse_github_url(url)
        if not parsed:
            logger.warning(f"Could not parse GitHub URL: {url}")
            return None

        owner, repo = parsed
        try:
            return await self.fetch_repo_info(owner, repo)
        except httpx.HTTPStatusError as e:
            logger.error(f"GitHub API error for {owner}/{repo}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching repo {owner}/{repo}: {e}")
            return None
