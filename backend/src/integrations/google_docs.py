"""Google Docs integration for import/export."""

import re
from typing import Any

import httpx
from pydantic import BaseModel


class GoogleDocContent(BaseModel):
    """Represents content extracted from a Google Doc."""

    title: str
    text: str
    doc_id: str
    pdf_bytes: bytes | None = None  # PDF export for hyperlink extraction


class GoogleDocsService:
    """Service for interacting with Google Docs.

    Note: This implementation uses a simplified approach that works with
    publicly shared documents. For full OAuth integration, you would need
    to implement the full Google OAuth2 flow.
    """

    EXPORT_URL_TXT = "https://docs.google.com/document/d/{doc_id}/export?format=txt"
    EXPORT_URL_PDF = "https://docs.google.com/document/d/{doc_id}/export?format=pdf"
    DOC_ID_PATTERN = re.compile(r"/document/d/([a-zA-Z0-9_-]+)")

    def __init__(self, credentials: dict[str, Any] | None = None):
        """Initialize the Google Docs service.

        Args:
            credentials: Optional OAuth2 credentials for authenticated access.
        """
        self.credentials = credentials
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            headers = {}
            if self.credentials and "access_token" in self.credentials:
                headers["Authorization"] = f"Bearer {self.credentials['access_token']}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    @classmethod
    def extract_doc_id(cls, url: str) -> str | None:
        """Extract the document ID from a Google Docs URL.

        Args:
            url: The Google Docs URL.

        Returns:
            The document ID or None if not found.
        """
        match = cls.DOC_ID_PATTERN.search(url)
        return match.group(1) if match else None

    async def fetch_document(self, url_or_id: str) -> GoogleDocContent:
        """Fetch content from a Google Doc.

        Args:
            url_or_id: Either a Google Docs URL or a document ID.

        Returns:
            The document content including PDF bytes for hyperlink extraction.

        Raises:
            ValueError: If the document ID cannot be extracted.
            httpx.HTTPError: If the document cannot be fetched.
        """
        # Extract doc ID if URL provided
        if url_or_id.startswith("http"):
            doc_id = self.extract_doc_id(url_or_id)
            if not doc_id:
                raise ValueError(f"Could not extract document ID from URL: {url_or_id}")
        else:
            doc_id = url_or_id

        client = await self._get_client()

        # Fetch as plain text (for quick title extraction)
        export_url_txt = self.EXPORT_URL_TXT.format(doc_id=doc_id)
        response = await client.get(export_url_txt, follow_redirects=True)
        response.raise_for_status()

        text = response.text

        # Extract title from first line or use default
        lines = text.strip().split("\n")
        title = lines[0] if lines else "Untitled Document"

        # Also fetch as PDF to preserve hyperlinks
        pdf_bytes = None
        try:
            export_url_pdf = self.EXPORT_URL_PDF.format(doc_id=doc_id)
            pdf_response = await client.get(export_url_pdf, follow_redirects=True)
            pdf_response.raise_for_status()
            pdf_bytes = pdf_response.content
        except Exception:
            # Fall back to text-only if PDF export fails
            pass

        return GoogleDocContent(
            title=title,
            text=text,
            doc_id=doc_id,
            pdf_bytes=pdf_bytes,
        )

    async def create_document(
        self,
        title: str,
        content: str,
    ) -> str:
        """Create a new Google Doc with the given content.

        Note: This requires OAuth2 credentials with write access.

        Args:
            title: The document title.
            content: The document content (plain text or HTML).

        Returns:
            The URL of the created document.

        Raises:
            ValueError: If credentials are not configured.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("OAuth2 credentials required to create documents")

        client = await self._get_client()

        # Create document using Google Docs API
        create_response = await client.post(
            "https://docs.googleapis.com/v1/documents",
            json={"title": title},
        )
        create_response.raise_for_status()
        doc_data = create_response.json()
        doc_id = doc_data["documentId"]

        # Insert content
        if content:
            await client.post(
                f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
                json={
                    "requests": [
                        {
                            "insertText": {
                                "location": {"index": 1},
                                "text": content,
                            }
                        }
                    ]
                },
            )

        return f"https://docs.google.com/document/d/{doc_id}/edit"

    async def create_ats_resume(
        self,
        title: str,
        resume_data: dict[str, Any],
    ) -> str:
        """Create an ATS-friendly formatted Google Doc resume.

        Args:
            title: The document title.
            resume_data: Resume JSON data with profile, experiences, projects, skills, publications.

        Returns:
            The URL of the created document.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("OAuth2 credentials required to create documents")

        client = await self._get_client()

        # Create empty document
        create_response = await client.post(
            "https://docs.googleapis.com/v1/documents",
            json={"title": title},
        )
        create_response.raise_for_status()
        doc_data = create_response.json()
        doc_id = doc_data["documentId"]

        # Build requests for ATS-friendly formatting
        requests = self._build_ats_resume_requests(resume_data)

        if requests:
            await client.post(
                f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
                json={"requests": requests},
            )

        return f"https://docs.google.com/document/d/{doc_id}/edit"

    def _build_ats_resume_requests(self, data: dict[str, Any]) -> list[dict[str, Any]]:
        """Build Google Docs API requests for ATS-friendly resume formatting.

        ATS Best Practices:
        - Simple, single-column layout
        - Standard section headers
        - No tables, graphics, or columns
        - Clear hierarchy with consistent formatting
        - Standard fonts (the doc will use default)
        """
        requests: list[dict[str, Any]] = []
        index = 1  # Google Docs uses 1-based indexing

        profile = data.get("profile", {})
        experiences = data.get("experiences", [])
        projects = data.get("projects", [])
        skills = data.get("skills", [])
        publications = data.get("publications", [])

        # === NAME (Large, Bold, Centered) ===
        name = profile.get("full_name") or "Resume"
        requests.append({"insertText": {"location": {"index": index}, "text": f"{name}\n"}})
        name_end = index + len(name)
        requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": index, "endIndex": name_end + 1},
                "paragraphStyle": {"alignment": "CENTER"},
                "fields": "alignment",
            }
        })
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": index, "endIndex": name_end},
                "textStyle": {"bold": True, "fontSize": {"magnitude": 18, "unit": "PT"}},
                "fields": "bold,fontSize",
            }
        })
        index = name_end + 1

        # === CONTACT INFO (Single line, centered) ===
        contact_parts = []
        if profile.get("email"):
            contact_parts.append(profile["email"])
        if profile.get("phone"):
            contact_parts.append(profile["phone"])
        if profile.get("location"):
            contact_parts.append(profile["location"])
        if profile.get("linkedin_url"):
            contact_parts.append(profile["linkedin_url"])
        if profile.get("websites"):
            contact_parts.extend(profile["websites"][:2])  # Max 2 websites

        if contact_parts:
            contact_line = " | ".join(contact_parts) + "\n"
            requests.append({"insertText": {"location": {"index": index}, "text": contact_line}})
            contact_end = index + len(contact_line) - 1
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": index, "endIndex": contact_end + 1},
                    "paragraphStyle": {"alignment": "CENTER"},
                    "fields": "alignment",
                }
            })
            requests.append({
                "updateTextStyle": {
                    "range": {"startIndex": index, "endIndex": contact_end},
                    "textStyle": {"fontSize": {"magnitude": 10, "unit": "PT"}},
                    "fields": "fontSize",
                }
            })
            index += len(contact_line)

        # Add spacing
        requests.append({"insertText": {"location": {"index": index}, "text": "\n"}})
        index += 1

        # === SUMMARY (if present) ===
        if profile.get("summary"):
            index = self._add_section_header(requests, index, "SUMMARY")
            summary_text = profile["summary"] + "\n\n"
            requests.append({"insertText": {"location": {"index": index}, "text": summary_text}})
            index += len(summary_text)

        # === EXPERIENCE ===
        if experiences:
            index = self._add_section_header(requests, index, "EXPERIENCE")

            for exp in experiences:
                # Role at Company (Bold)
                role_line = f"{exp.get('role', 'Role')} at {exp.get('company', 'Company')}\n"
                requests.append({"insertText": {"location": {"index": index}, "text": role_line}})
                role_end = index + len(role_line) - 1
                requests.append({
                    "updateTextStyle": {
                        "range": {"startIndex": index, "endIndex": role_end},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                })
                index += len(role_line)

                # Location | Dates (Italic)
                meta_parts = []
                if exp.get("location"):
                    meta_parts.append(exp["location"])
                date_str = self._format_date_range(
                    exp.get("start_date"),
                    exp.get("end_date"),
                    exp.get("is_current", False)
                )
                if date_str:
                    meta_parts.append(date_str)

                if meta_parts:
                    meta_line = " | ".join(meta_parts) + "\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": meta_line}})
                    meta_end = index + len(meta_line) - 1
                    requests.append({
                        "updateTextStyle": {
                            "range": {"startIndex": index, "endIndex": meta_end},
                            "textStyle": {"italic": True, "fontSize": {"magnitude": 10, "unit": "PT"}},
                            "fields": "italic,fontSize",
                        }
                    })
                    index += len(meta_line)

                # Bullets
                for bullet in exp.get("bullets", []):
                    bullet_text = f"• {bullet.get('content', '')}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": bullet_text}})
                    index += len(bullet_text)

                # Spacing between experiences
                requests.append({"insertText": {"location": {"index": index}, "text": "\n"}})
                index += 1

        # === PROJECTS ===
        if projects:
            index = self._add_section_header(requests, index, "PROJECTS")

            for proj in projects:
                # Project Name (Bold)
                proj_line = f"{proj.get('name', 'Project')}\n"
                requests.append({"insertText": {"location": {"index": index}, "text": proj_line}})
                proj_end = index + len(proj_line) - 1
                requests.append({
                    "updateTextStyle": {
                        "range": {"startIndex": index, "endIndex": proj_end},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                })
                index += len(proj_line)

                # Technologies (Italic)
                if proj.get("technologies"):
                    tech_line = f"Technologies: {', '.join(proj['technologies'])}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": tech_line}})
                    tech_end = index + len(tech_line) - 1
                    requests.append({
                        "updateTextStyle": {
                            "range": {"startIndex": index, "endIndex": tech_end},
                            "textStyle": {"italic": True, "fontSize": {"magnitude": 10, "unit": "PT"}},
                            "fields": "italic,fontSize",
                        }
                    })
                    index += len(tech_line)

                # Description
                if proj.get("description"):
                    desc_text = proj["description"] + "\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": desc_text}})
                    index += len(desc_text)

                # Bullets
                for bullet in proj.get("bullets", []):
                    bullet_text = f"• {bullet.get('content', '')}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": bullet_text}})
                    index += len(bullet_text)

                # Links
                if proj.get("links"):
                    links_text = "Links: " + " | ".join(
                        link.get("url", "") for link in proj["links"] if link.get("url")
                    ) + "\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": links_text}})
                    index += len(links_text)

                # Spacing
                requests.append({"insertText": {"location": {"index": index}, "text": "\n"}})
                index += 1

        # === SKILLS ===
        if skills:
            index = self._add_section_header(requests, index, "SKILLS")
            skills_text = ", ".join(skills) + "\n\n"
            requests.append({"insertText": {"location": {"index": index}, "text": skills_text}})
            index += len(skills_text)

        # === PUBLICATIONS ===
        if publications:
            index = self._add_section_header(requests, index, "PUBLICATIONS")

            for pub in publications:
                # Title (Bold)
                pub_title = pub.get("title", "Untitled")
                title_line = f"{pub_title}\n"
                requests.append({"insertText": {"location": {"index": index}, "text": title_line}})
                title_end = index + len(title_line) - 1
                requests.append({
                    "updateTextStyle": {
                        "range": {"startIndex": index, "endIndex": title_end},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                })
                index += len(title_line)

                # Authors, Venue, Date
                pub_meta = []
                if pub.get("authors"):
                    authors = pub["authors"]
                    if isinstance(authors, list):
                        authors = ", ".join(authors)
                    pub_meta.append(authors)
                if pub.get("venue"):
                    pub_meta.append(pub["venue"])
                if pub.get("publication_date"):
                    pub_meta.append(pub["publication_date"])

                if pub_meta:
                    meta_line = " | ".join(pub_meta) + "\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": meta_line}})
                    meta_end = index + len(meta_line) - 1
                    requests.append({
                        "updateTextStyle": {
                            "range": {"startIndex": index, "endIndex": meta_end},
                            "textStyle": {"italic": True, "fontSize": {"magnitude": 10, "unit": "PT"}},
                            "fields": "italic,fontSize",
                        }
                    })
                    index += len(meta_line)

                # DOI or URL
                if pub.get("doi"):
                    doi_line = f"DOI: {pub['doi']}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": doi_line}})
                    index += len(doi_line)
                elif pub.get("url"):
                    url_line = f"{pub['url']}\n"
                    requests.append({"insertText": {"location": {"index": index}, "text": url_line}})
                    index += len(url_line)

                # Spacing
                requests.append({"insertText": {"location": {"index": index}, "text": "\n"}})
                index += 1

        return requests

    def _add_section_header(
        self,
        requests: list[dict[str, Any]],
        index: int,
        header_text: str,
    ) -> int:
        """Add a section header with ATS-friendly formatting."""
        # Header line with underline effect using a separator
        header_line = f"{header_text}\n"
        separator = "─" * 50 + "\n"

        requests.append({"insertText": {"location": {"index": index}, "text": header_line}})
        header_end = index + len(header_line) - 1
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": index, "endIndex": header_end},
                "textStyle": {"bold": True, "fontSize": {"magnitude": 12, "unit": "PT"}},
                "fields": "bold,fontSize",
            }
        })
        index += len(header_line)

        requests.append({"insertText": {"location": {"index": index}, "text": separator}})
        sep_end = index + len(separator) - 1
        requests.append({
            "updateTextStyle": {
                "range": {"startIndex": index, "endIndex": sep_end},
                "textStyle": {"fontSize": {"magnitude": 8, "unit": "PT"}},
                "fields": "fontSize",
            }
        })
        index += len(separator)

        return index

    def _format_date_range(
        self,
        start_date: str | None,
        end_date: str | None,
        is_current: bool,
    ) -> str:
        """Format date range for display."""
        if not start_date:
            return ""

        # Parse and format dates (assuming ISO format YYYY-MM-DD)
        try:
            from datetime import datetime
            start = datetime.fromisoformat(start_date)
            start_str = start.strftime("%b %Y")
        except (ValueError, TypeError):
            start_str = start_date[:7] if start_date and len(start_date) >= 7 else start_date

        if is_current:
            return f"{start_str} - Present"
        elif end_date:
            try:
                end = datetime.fromisoformat(end_date)
                end_str = end.strftime("%b %Y")
            except (ValueError, TypeError):
                end_str = end_date[:7] if end_date and len(end_date) >= 7 else end_date
            return f"{start_str} - {end_str}"
        else:
            return start_str


class GoogleDriveService:
    """Service for interacting with Google Drive."""

    def __init__(self, credentials: dict[str, Any] | None = None):
        """Initialize the Google Drive service."""
        self.credentials = credentials
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            headers = {}
            if self.credentials and "access_token" in self.credentials:
                headers["Authorization"] = f"Bearer {self.credentials['access_token']}"
            self._client = httpx.AsyncClient(headers=headers, timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def upload_file(
        self,
        name: str,
        content: bytes,
        mime_type: str,
        folder_id: str | None = None,
    ) -> str:
        """Upload a file to Google Drive.

        Args:
            name: The file name.
            content: The file content.
            mime_type: The MIME type.
            folder_id: Optional folder ID to upload to.

        Returns:
            The file ID.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("OAuth2 credentials required to upload files")

        client = await self._get_client()

        metadata: dict[str, Any] = {"name": name}
        if folder_id:
            metadata["parents"] = [folder_id]

        # Use multipart upload
        files = {
            "metadata": ("metadata", metadata, "application/json"),
            "file": (name, content, mime_type),
        }

        response = await client.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            files=files,
        )
        response.raise_for_status()

        return response.json()["id"]

    async def list_files(
        self,
        folder_id: str | None = None,
        mime_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """List files in Google Drive.

        Args:
            folder_id: Optional folder ID to list files from.
            mime_type: Optional MIME type filter.

        Returns:
            List of file metadata.
        """
        if not self.credentials or "access_token" not in self.credentials:
            raise ValueError("OAuth2 credentials required to list files")

        client = await self._get_client()

        query_parts = []
        if folder_id:
            query_parts.append(f"'{folder_id}' in parents")
        if mime_type:
            query_parts.append(f"mimeType='{mime_type}'")

        params = {"fields": "files(id,name,mimeType,modifiedTime)"}
        if query_parts:
            params["q"] = " and ".join(query_parts)

        response = await client.get(
            "https://www.googleapis.com/drive/v3/files",
            params=params,
        )
        response.raise_for_status()

        return response.json().get("files", [])
