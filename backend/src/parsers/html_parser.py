"""HTML parser for job description pages."""

import re

from bs4 import BeautifulSoup
from markdownify import markdownify


class HTMLParser:
    """Parse HTML content and convert to clean text/markdown."""

    # Common job site selectors for main content
    CONTENT_SELECTORS = [
        # LinkedIn
        'div.description__text',
        'div.show-more-less-html__markup',
        # Indeed
        'div#jobDescriptionText',
        'div.jobsearch-jobDescriptionText',
        # Greenhouse
        'div#content',
        'div.content',
        # Lever
        'div.section-wrapper',
        # Generic
        'article',
        'main',
        'div[role="main"]',
        'div.job-description',
        'div.job-details',
        'div.posting-requirements',
    ]

    # Elements to remove
    REMOVE_SELECTORS = [
        'script',
        'style',
        'nav',
        'header',
        'footer',
        'aside',
        'form',
        'button',
        'input',
        'iframe',
        '.advertisement',
        '.sidebar',
        '.related-jobs',
        '.apply-button',
    ]

    @classmethod
    def parse(cls, html_content: str, convert_to_markdown: bool = True) -> str:
        """Parse HTML and extract main content.

        Args:
            html_content: Raw HTML string.
            convert_to_markdown: If True, convert to markdown; otherwise plain text.

        Returns:
            Extracted and cleaned content.
        """
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove unwanted elements
        for selector in cls.REMOVE_SELECTORS:
            for element in soup.select(selector):
                element.decompose()

        # Try to find main content using selectors
        main_content = None
        for selector in cls.CONTENT_SELECTORS:
            elements = soup.select(selector)
            if elements:
                # Get the largest content block
                main_content = max(elements, key=lambda x: len(x.get_text()))
                break

        # Fall back to body if no specific content found
        if main_content is None:
            main_content = soup.body or soup

        if convert_to_markdown:
            # Convert to markdown
            markdown = markdownify(
                str(main_content),
                heading_style="ATX",
                bullets="-",
                strip=['a'],  # Remove links but keep text
            )
            # Clean up excessive whitespace
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)
            markdown = re.sub(r' {2,}', ' ', markdown)
            return markdown.strip()
        else:
            # Plain text extraction
            text = main_content.get_text(separator='\n', strip=True)
            # Clean up
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()

    @staticmethod
    def extract_job_metadata(html_content: str) -> dict:
        """Extract structured metadata from job posting HTML.

        Args:
            html_content: Raw HTML string.

        Returns:
            Dictionary with extracted metadata (title, company, location, etc.)
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {}

        # Try to extract title
        title_selectors = [
            'h1.job-title',
            'h1.posting-headline',
            'h1[data-test="job-title"]',
            'h1',
        ]
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                metadata['title'] = element.get_text(strip=True)
                break

        # Try to extract company
        company_selectors = [
            'a.company-name',
            'span.company',
            '[data-test="employer-name"]',
            '.posting-categories .department',
        ]
        for selector in company_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                metadata['company'] = element.get_text(strip=True)
                break

        # Try to extract location
        location_selectors = [
            'span.location',
            '[data-test="job-location"]',
            '.posting-categories .location',
        ]
        for selector in location_selectors:
            element = soup.select_one(selector)
            if element and element.get_text(strip=True):
                metadata['location'] = element.get_text(strip=True)
                break

        return metadata
