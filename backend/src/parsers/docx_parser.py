"""DOCX document parser using python-docx with hyperlink extraction."""

import re
from pathlib import Path
from typing import BinaryIO

from docx import Document
from docx.oxml.ns import qn


class DocxParser:
    """Parse DOCX documents and extract text content with hyperlinks."""

    @staticmethod
    def _extract_hyperlinks(doc) -> list[str]:
        """Extract all hyperlinks from a DOCX document.

        Args:
            doc: python-docx Document object.

        Returns:
            List of URLs found in the document.
        """
        links = []
        try:
            # Get the document part's relationships
            rels = doc.part.rels

            # Iterate through all relationships to find hyperlinks
            for rel_id, rel in rels.items():
                if rel.reltype == "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink":
                    if rel.target_ref:
                        links.append(rel.target_ref)

            # Also search through the document XML for any hyperlinks we might have missed
            # This catches hyperlinks in the main body
            for para in doc.paragraphs:
                for run in para.runs:
                    # Check the underlying XML for hyperlink references
                    xml_element = run._element
                    parent = xml_element.getparent()
                    if parent is not None:
                        # Look for hyperlink elements in parent
                        for ancestor in xml_element.iterancestors():
                            if ancestor.tag == qn('w:hyperlink'):
                                # Get the relationship ID
                                r_id = ancestor.get(qn('r:id'))
                                if r_id and r_id in rels:
                                    rel = rels[r_id]
                                    if rel.target_ref and rel.target_ref not in links:
                                        links.append(rel.target_ref)
                                break

        except Exception:
            pass  # Silently ignore hyperlink extraction errors

        return links

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
    def _format_links_section(all_links: list[str]) -> str:
        """Format extracted links into a section for the document.

        Args:
            all_links: List of URLs found in the document.

        Returns:
            Formatted links section string.
        """
        if not all_links:
            return ""

        # Deduplicate and filter valid URLs
        unique_links = []
        seen = set()
        for url in all_links:
            url = url.strip()
            if url and url not in seen and url.startswith(('http://', 'https://')):
                unique_links.append(url)
                seen.add(url)

        if not unique_links:
            return ""

        # Categorize links
        github_links = [u for u in unique_links if 'github.com' in u.lower()]
        linkedin_links = [u for u in unique_links if 'linkedin.com' in u.lower()]
        other_links = [u for u in unique_links if u not in github_links and u not in linkedin_links]

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
    def _extract_text_and_links(doc) -> tuple[list[str], list[str]]:
        """Extract text paragraphs and hyperlinks from document.

        Args:
            doc: python-docx Document object.

        Returns:
            Tuple of (paragraphs list, links list).
        """
        paragraphs = []
        all_links = []

        # Extract text from paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                paragraphs.append(para.text)
                # Extract URLs from text
                all_links.extend(DocxParser._extract_urls_from_text(para.text))

        # Extract from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    if cell.text.strip():
                        row_text.append(cell.text.strip())
                        all_links.extend(DocxParser._extract_urls_from_text(cell.text))
                if row_text:
                    paragraphs.append(" | ".join(row_text))

        # Extract hyperlinks from document relationships
        hyperlinks = DocxParser._extract_hyperlinks(doc)
        all_links.extend(hyperlinks)

        return paragraphs, all_links

    @staticmethod
    def parse(file_path: str | Path) -> str:
        """Extract text and hyperlinks from a DOCX file path.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Extracted text content with hyperlinks section appended.

        Raises:
            ValueError: If the file cannot be parsed.
        """
        try:
            doc = Document(file_path)
            paragraphs, all_links = DocxParser._extract_text_and_links(doc)

            text_content = "\n\n".join(paragraphs)

            # Append hyperlinks section
            links_section = DocxParser._format_links_section(all_links)
            if links_section:
                text_content += links_section

            return text_content
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX: {e}") from e

    @staticmethod
    def parse_bytes(file_content: BinaryIO) -> str:
        """Extract text and hyperlinks from DOCX file content.

        Args:
            file_content: Binary file-like object containing DOCX data.

        Returns:
            Extracted text content with hyperlinks section appended.

        Raises:
            ValueError: If the content cannot be parsed.
        """
        try:
            doc = Document(file_content)
            paragraphs, all_links = DocxParser._extract_text_and_links(doc)

            text_content = "\n\n".join(paragraphs)

            # Append hyperlinks section
            links_section = DocxParser._format_links_section(all_links)
            if links_section:
                text_content += links_section

            return text_content
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX content: {e}") from e

    @staticmethod
    def get_metadata(file_path: str | Path) -> dict:
        """Extract metadata from a DOCX file.

        Args:
            file_path: Path to the DOCX file.

        Returns:
            Dictionary containing DOCX metadata.
        """
        try:
            doc = Document(file_path)
            core_props = doc.core_properties

            return {
                "title": core_props.title or "",
                "author": core_props.author or "",
                "created": str(core_props.created) if core_props.created else "",
                "modified": str(core_props.modified) if core_props.modified else "",
                "paragraph_count": len(doc.paragraphs),
            }
        except Exception:
            return {}
