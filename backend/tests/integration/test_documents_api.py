"""Integration tests for documents API."""

import pytest
from httpx import AsyncClient
from io import BytesIO


@pytest.mark.asyncio
class TestDocumentUpload:
    """Test document upload functionality."""

    async def test_upload_pdf_success(
        self,
        client: AsyncClient,
        sample_pdf_content: bytes,
    ):
        """Test successful PDF upload."""
        files = {
            "file": ("resume.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }

        response = await client.post("/documents/upload", files=files)

        assert response.status_code == 201
        data = response.json()
        assert data["filename"] == "resume.pdf"
        assert data["mime_type"] == "application/pdf"
        assert data["processing_status"] == "pending"
        assert "id" in data

    async def test_upload_file_too_large(self, client: AsyncClient):
        """Test uploading file that exceeds size limit."""
        # Create a large file (11MB)
        large_content = b"x" * (11 * 1024 * 1024)
        files = {
            "file": ("large.pdf", BytesIO(large_content), "application/pdf")
        }

        response = await client.post("/documents/upload", files=files)

        assert response.status_code == 413

    async def test_upload_invalid_file_type(self, client: AsyncClient):
        """Test uploading unsupported file type."""
        files = {
            "file": ("script.js", BytesIO(b"console.log('test')"), "text/javascript")
        }

        response = await client.post("/documents/upload", files=files)

        assert response.status_code == 415


@pytest.mark.asyncio
class TestDocumentList:
    """Test document listing functionality."""

    async def test_list_documents_empty(self, client: AsyncClient):
        """Test listing documents when none exist."""
        response = await client.get("/documents")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_documents_with_data(
        self,
        client: AsyncClient,
        sample_pdf_content: bytes,
    ):
        """Test listing documents after upload."""
        # Upload a document first
        files = {
            "file": ("resume.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        await client.post("/documents/upload", files=files)

        # List documents
        response = await client.get("/documents")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1
        assert data["items"][0]["filename"] == "resume.pdf"


@pytest.mark.asyncio
class TestDocumentOperations:
    """Test document operations (get, verify, delete)."""

    async def test_get_document(
        self,
        client: AsyncClient,
        sample_pdf_content: bytes,
    ):
        """Test getting a specific document."""
        # Upload a document first
        files = {
            "file": ("resume.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        upload_response = await client.post("/documents/upload", files=files)
        doc_id = upload_response.json()["id"]

        # Get the document
        response = await client.get(f"/documents/{doc_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id
        assert data["filename"] == "resume.pdf"

    async def test_get_nonexistent_document(self, client: AsyncClient):
        """Test getting a document that doesn't exist."""
        from uuid import uuid4

        response = await client.get(f"/documents/{uuid4()}")

        assert response.status_code == 404

    async def test_verify_document(
        self,
        client: AsyncClient,
        sample_pdf_content: bytes,
    ):
        """Test verifying document classification."""
        # Upload a document first
        files = {
            "file": ("resume.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        upload_response = await client.post("/documents/upload", files=files)
        doc_id = upload_response.json()["id"]

        # Verify classification
        response = await client.put(
            f"/documents/{doc_id}/verify",
            json={"document_class": "experience"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["document_class"] == "experience"
        assert data["verified_by_user"] is True

    async def test_delete_document(
        self,
        client: AsyncClient,
        sample_pdf_content: bytes,
    ):
        """Test deleting a document."""
        # Upload a document first
        files = {
            "file": ("resume.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        upload_response = await client.post("/documents/upload", files=files)
        doc_id = upload_response.json()["id"]

        # Delete the document
        response = await client.delete(f"/documents/{doc_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/documents/{doc_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
class TestDocumentIsolation:
    """Test that users can only access their own documents."""

    async def test_cannot_access_other_users_documents(
        self,
        client: AsyncClient,
        unauthenticated_client: AsyncClient,
        sample_pdf_content: bytes,
    ):
        """Test that documents are isolated between users."""
        # Upload a document as test user
        files = {
            "file": ("resume.pdf", BytesIO(sample_pdf_content), "application/pdf")
        }
        upload_response = await client.post("/documents/upload", files=files)
        doc_id = upload_response.json()["id"]

        # Create another user and try to access
        # Register new user
        await unauthenticated_client.post(
            "/auth/register",
            json={
                "email": "other@example.com",
                "password": "password123",
            },
        )

        # Login as new user
        login_response = await unauthenticated_client.post(
            "/auth/login",
            json={
                "email": "other@example.com",
                "password": "password123",
            },
        )
        other_token = login_response.json()["access_token"]

        # Try to access first user's document
        response = await unauthenticated_client.get(
            f"/documents/{doc_id}",
            headers={"Authorization": f"Bearer {other_token}"},
        )

        assert response.status_code == 404  # Should not find it
