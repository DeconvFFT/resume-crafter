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
