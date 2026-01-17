"""PDF document parser using pdfplumber with hyperlink extraction via PyMuPDF."""

import re
from pathlib import Path
from typing import BinaryIO

import pdfplumber

# PyMuPDF is more reliable for extracting hyperlinks
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


class PDFParser:
    """Parse PDF documents and extract text content with hyperlinks."""

    @staticmethod
    def _extract_hyperlinks_pymupdf(file_path: str | Path) -> list[str]:
        """Extract hyperlinks from PDF using PyMuPDF (more reliable).

        Args:
            file_path: Path to the PDF file.

        Returns:
            List of URLs found in the document.
        """
        if not HAS_PYMUPDF:
            return []

        links = []
        try:
            doc = fitz.open(file_path)
            for page in doc:
                # Get all links from the page
                page_links = page.get_links()
                for link in page_links:
                    # Check for URI links (external URLs)
                    if link.get('kind') == fitz.LINK_URI:
                        uri = link.get('uri', '')
                        if uri and uri.startswith(('http://', 'https://')):
                            links.append(uri)
                    # Also check the 'uri' key directly
                    elif 'uri' in link:
                        uri = link['uri']
                        if uri and uri.startswith(('http://', 'https://')):
                            links.append(uri)

                # Also extract links from annotations
                for annot in page.annots() or []:
                    if annot.type[0] == fitz.PDF_ANNOT_LINK:
                        info = annot.info
                        if 'uri' in info:
                            uri = info['uri']
                            if uri and uri.startswith(('http://', 'https://')):
                                links.append(uri)
            doc.close()
        except Exception as e:
            pass  # Silently ignore extraction errors
        return links

    @staticmethod
    def _extract_hyperlinks_pymupdf_bytes(file_content: BinaryIO) -> list[str]:
        """Extract hyperlinks from PDF bytes using PyMuPDF.

        Args:
            file_content: Binary file-like object containing PDF data.

        Returns:
            List of URLs found in the document.
        """
        if not HAS_PYMUPDF:
            return []

        links = []
        try:
            # Read bytes and open with PyMuPDF
            data = file_content.read()
            file_content.seek(0)  # Reset for pdfplumber
            doc = fitz.open(stream=data, filetype="pdf")
            for page in doc:
                page_links = page.get_links()
                for link in page_links:
                    if link.get('kind') == fitz.LINK_URI:
                        uri = link.get('uri', '')
                        if uri and uri.startswith(('http://', 'https://')):
                            links.append(uri)
                    elif 'uri' in link:
                        uri = link['uri']
                        if uri and uri.startswith(('http://', 'https://')):
                            links.append(uri)
            doc.close()
        except Exception:
            pass
        return links

    @staticmethod
    def _extract_hyperlinks_pdfplumber(page) -> list[str]:
        """Extract hyperlinks from a PDF page using pdfplumber (fallback).

        Args:
            page: pdfplumber page object.

        Returns:
            List of URLs found.
        """
        links = []
        try:
            # pdfplumber exposes annotations via page.annots
            if hasattr(page, 'annots') and page.annots:
                for annot in page.annots:
                    uri = annot.get('uri') or annot.get('A', {}).get('URI')
                    if uri and uri.startswith(('http://', 'https://')):
                        links.append(uri)

            # Also check hyperlinks attribute
            if hasattr(page, 'hyperlinks') and page.hyperlinks:
                for link in page.hyperlinks:
                    uri = link.get('uri')
                    if uri and uri.startswith(('http://', 'https://')):
                        links.append(uri)
        except Exception:
            pass
        return links

    @staticmethod
    def _is_valid_github_repo_url(url: str) -> bool:
        """Check if URL is a valid GitHub repository URL (not just a user/org page).

        Args:
            url: URL to validate.

        Returns:
            True if URL points to a specific repository.
        """
        import re
        # Match github.com/owner/repo pattern (repo must have at least 1 char)
        pattern = r'https?://github\.com/[^/]+/[^/]+'
        return bool(re.match(pattern, url))

    @staticmethod
    def _format_links_section(all_links: list[str]) -> str:
        """Format extracted links into a section for the document.

        Args:
            all_links: List of unique URLs found in the document.

        Returns:
            Formatted links section string.
        """
        if not all_links:
            return ""

        # Deduplicate, preferring longer/more complete URLs
        url_map = {}  # base -> longest URL
        for url in all_links:
            url = url.strip()
            if not url or not url.startswith(('http://', 'https://')):
                continue
            # Use a normalized base for deduplication
            base = url.rstrip('/').lower()
            # Keep the longer URL (more complete)
            if base not in url_map or len(url) > len(url_map[base]):
                url_map[base] = url

        unique_links = list(url_map.values())

        if not unique_links:
            return ""

        # Categorize links - filter out incomplete GitHub URLs
        github_links = []
        for u in unique_links:
            if 'github.com' in u.lower():
                # Only include valid repo URLs, not user/org pages
                if PDFParser._is_valid_github_repo_url(u):
                    github_links.append(u)
        linkedin_links = [u for u in unique_links if 'linkedin.com' in u.lower()]
        other_links = [u for u in unique_links if u not in github_links and u not in linkedin_links and 'github.com' not in u.lower()]

        sections = ["\n\n--- EXTRACTED HYPERLINKS ---"]

        if github_links:
            sections.append("\nGitHub Links:")
            for url in github_links:
                sections.append(f"  - {url}")

        if linkedin_links:
            sections.append("\nLinkedIn Links:")
            for url in linkedin_links:
                sections.append(f"  - {url}")

        if other_links:
            sections.append("\nOther Links:")
            for url in other_links:
                sections.append(f"  - {url}")

        sections.append("--- END HYPERLINKS ---\n")

        return "\n".join(sections)

    @staticmethod
    def _extract_urls_from_text(text: str) -> list[str]:
        """Extract URLs that appear as plain text in the document.

        Args:
            text: Extracted text content.

        Returns:
            List of URLs found in text.
        """
        # Regex to match URLs in text
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, text)
        # Clean up trailing punctuation
        cleaned = []
        for url in urls:
            url = url.rstrip('.,;:!?)>]')
            if url:
                cleaned.append(url)
        return cleaned

    @staticmethod
    def parse(file_path: str | Path) -> str:
        """Extract text and hyperlinks from a PDF file path.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted text content with hyperlinks section appended.

        Raises:
            ValueError: If the file cannot be parsed.
        """
        try:
            text_parts = []
            all_links = []

            # First, extract hyperlinks using PyMuPDF (more reliable)
            pymupdf_links = PDFParser._extract_hyperlinks_pymupdf(file_path)
            all_links.extend(pymupdf_links)

            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                        # Also find URLs in the text itself
                        all_links.extend(PDFParser._extract_urls_from_text(page_text))

                    # Fallback: also try pdfplumber's annotation extraction
                    pdfplumber_links = PDFParser._extract_hyperlinks_pdfplumber(page)
                    all_links.extend(pdfplumber_links)

            text_content = "\n\n".join(text_parts)

            # Append hyperlinks section
            links_section = PDFParser._format_links_section(all_links)
            if links_section:
                text_content += links_section

            return text_content
        except Exception as e:
            raise ValueError(f"Failed to parse PDF: {e}") from e

    @staticmethod
    def parse_bytes(file_content: BinaryIO) -> str:
        """Extract text and hyperlinks from PDF file content.

        Args:
            file_content: Binary file-like object containing PDF data.

        Returns:
            Extracted text content with hyperlinks section appended.

        Raises:
            ValueError: If the content cannot be parsed.
        """
        try:
            text_parts = []
            all_links = []

            # First, extract hyperlinks using PyMuPDF (more reliable)
            pymupdf_links = PDFParser._extract_hyperlinks_pymupdf_bytes(file_content)
            all_links.extend(pymupdf_links)

            with pdfplumber.open(file_content) as pdf:
                for page in pdf.pages:
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                        # Also find URLs in the text itself
                        all_links.extend(PDFParser._extract_urls_from_text(page_text))

                    # Fallback: also try pdfplumber's annotation extraction
                    pdfplumber_links = PDFParser._extract_hyperlinks_pdfplumber(page)
                    all_links.extend(pdfplumber_links)

            text_content = "\n\n".join(text_parts)

            # Append hyperlinks section
            links_section = PDFParser._format_links_section(all_links)
            if links_section:
                text_content += links_section

            return text_content
        except Exception as e:
            raise ValueError(f"Failed to parse PDF content: {e}") from e

    @staticmethod
    def get_metadata(file_path: str | Path) -> dict:
        """Extract metadata from a PDF file.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Dictionary containing PDF metadata.
        """
        try:
            with pdfplumber.open(file_path) as pdf:
                return {
                    "page_count": len(pdf.pages),
                    "metadata": pdf.metadata or {},
                }
        except Exception:
            return {"page_count": 0, "metadata": {}}
