"""Job site scraping with Playwright fallback."""

import asyncio
import re
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from markdownify import markdownify
from pydantic import BaseModel


class ScrapedJobContent(BaseModel):
    """Represents scraped job content."""

    url: str
    title: str | None
    company: str | None
    text: str
    html: str


class JobScraper:
    """Job scraper with HTTP and Playwright fallback."""

    # User agent for requests
    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Known job site patterns for better extraction
    JOB_SITE_PATTERNS = {
        "linkedin.com": {
            "title_selector": ".top-card-layout__title",
            "company_selector": ".topcard__org-name-link",
            "description_selector": ".description__text",
        },
        "greenhouse.io": {
            "title_selector": ".app-title",
            "company_selector": ".company-name",
            "description_selector": "#content",
        },
        "lever.co": {
            "title_selector": ".posting-headline h2",
            "company_selector": ".posting-headline a",
            "description_selector": ".posting-page",
        },
        "indeed.com": {
            "title_selector": ".jobsearch-JobInfoHeader-title",
            "company_selector": "[data-company-name]",
            "description_selector": "#jobDescriptionText",
        },
        "glassdoor.com": {
            "title_selector": ".job-title",
            "company_selector": ".employer-name",
            "description_selector": ".jobDescriptionContent",
        },
    }

    def __init__(self):
        """Initialize the job scraper."""
        self._client: httpx.AsyncClient | None = None
        self._playwright = None
        self._browser = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers={"User-Agent": self.USER_AGENT},
                follow_redirects=True,
                timeout=30.0,
            )
        return self._client

    async def _get_browser(self):
        """Get or create Playwright browser."""
        if self._browser is None:
            try:
                from playwright.async_api import async_playwright

                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(headless=True)
            except ImportError:
                raise ImportError(
                    "Playwright not installed. Install with: pip install playwright && playwright install chromium"
                )
        return self._browser

    async def close(self) -> None:
        """Close resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    def _get_site_pattern(self, url: str) -> dict[str, str] | None:
        """Get extraction pattern for known job sites."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for site, pattern in self.JOB_SITE_PATTERNS.items():
            if site in domain:
                return pattern
        return None

    def _extract_metadata(
        self, soup: BeautifulSoup, pattern: dict[str, str] | None
    ) -> tuple[str | None, str | None]:
        """Extract title and company from HTML."""
        title = None
        company = None

        if pattern:
            # Use site-specific selectors
            title_el = soup.select_one(pattern.get("title_selector", ""))
            if title_el:
                title = title_el.get_text(strip=True)

            company_el = soup.select_one(pattern.get("company_selector", ""))
            if company_el:
                company = company_el.get_text(strip=True)
        else:
            # Generic extraction
            # Try common title patterns
            for selector in ["h1", ".job-title", "[class*='title']", "title"]:
                el = soup.select_one(selector)
                if el:
                    title = el.get_text(strip=True)
                    break

            # Try common company patterns
            for selector in [
                "[class*='company']",
                "[class*='employer']",
                "[class*='org']",
            ]:
                el = soup.select_one(selector)
                if el:
                    company = el.get_text(strip=True)
                    break

        return title, company

    def _extract_description(
        self, soup: BeautifulSoup, pattern: dict[str, str] | None
    ) -> str:
        """Extract job description from HTML."""
        if pattern:
            desc_el = soup.select_one(pattern.get("description_selector", ""))
            if desc_el:
                return str(desc_el)

        # Generic extraction - try common description containers
        for selector in [
            "#jobDescription",
            ".job-description",
            "[class*='description']",
            "article",
            "main",
            ".content",
        ]:
            el = soup.select_one(selector)
            if el and len(el.get_text(strip=True)) > 200:
                return str(el)

        # Fallback to body
        body = soup.find("body")
        return str(body) if body else str(soup)

    async def scrape_http(self, url: str) -> ScrapedJobContent | None:
        """Try to scrape using simple HTTP request."""
        try:
            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()

            html = response.text
            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            pattern = self._get_site_pattern(url)
            title, company = self._extract_metadata(soup, pattern)
            description_html = self._extract_description(soup, pattern)

            # Convert to markdown
            text = markdownify(description_html, strip=["a", "img"])
            # Clean up excessive whitespace
            text = re.sub(r"\n{3,}", "\n\n", text.strip())

            return ScrapedJobContent(
                url=url,
                title=title,
                company=company,
                text=text,
                html=description_html,
            )

        except (httpx.HTTPError, httpx.TimeoutException):
            return None

    async def scrape_playwright(self, url: str) -> ScrapedJobContent:
        """Scrape using Playwright for JavaScript-rendered content."""
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until="networkidle")

            # Wait for common job description elements
            for selector in [
                "[class*='description']",
                "[class*='job']",
                "article",
                "main",
            ]:
                try:
                    await page.wait_for_selector(selector, timeout=5000)
                    break
                except Exception:
                    continue

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            pattern = self._get_site_pattern(url)
            title, company = self._extract_metadata(soup, pattern)
            description_html = self._extract_description(soup, pattern)

            # Convert to markdown
            text = markdownify(description_html, strip=["a", "img"])
            text = re.sub(r"\n{3,}", "\n\n", text.strip())

            return ScrapedJobContent(
                url=url,
                title=title,
                company=company,
                text=text,
                html=description_html,
            )

        finally:
            await page.close()

    async def scrape(self, url: str) -> ScrapedJobContent:
        """Scrape job posting with fallback to Playwright.

        Args:
            url: The job posting URL.

        Returns:
            Scraped job content.

        Raises:
            Exception: If scraping fails completely.
        """
        # Try simple HTTP first
        result = await self.scrape_http(url)

        if result and len(result.text) > 100:
            return result

        # Fallback to Playwright for JS-rendered content
        try:
            return await self.scrape_playwright(url)
        except ImportError:
            # Playwright not available, return HTTP result if any
            if result:
                return result
            raise ValueError(
                f"Could not scrape job posting from {url}. "
                "Install Playwright for better results: pip install playwright && playwright install chromium"
            )


async def scrape_job_url(url: str) -> ScrapedJobContent:
    """Convenience function to scrape a job URL.

    Args:
        url: The job posting URL.

    Returns:
        Scraped job content.
    """
    scraper = JobScraper()
    try:
        return await scraper.scrape(url)
    finally:
        await scraper.close()
