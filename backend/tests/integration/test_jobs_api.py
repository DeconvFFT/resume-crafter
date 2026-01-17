"""Integration tests for jobs API."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestJobAnalysis:
    """Test job analysis functionality."""

    async def test_analyze_job_with_text(
        self,
        client: AsyncClient,
        sample_job_description: str,
    ):
        """Test analyzing a job from text."""
        response = await client.post(
            "/jobs/analyze",
            json={"raw_text": sample_job_description},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["processing_status"] == "pending"

    async def test_analyze_job_with_url(self, client: AsyncClient):
        """Test analyzing a job from URL."""
        response = await client.post(
            "/jobs/analyze",
            json={"source_url": "https://example.com/job/123"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["source_url"] == "https://example.com/job/123"

    async def test_analyze_job_no_input(self, client: AsyncClient):
        """Test analyzing without URL or text."""
        response = await client.post(
            "/jobs/analyze",
            json={},
        )

        # Should fail - need either URL or text
        assert response.status_code == 400


@pytest.mark.asyncio
class TestJobList:
    """Test job listing functionality."""

    async def test_list_jobs_empty(self, client: AsyncClient):
        """Test listing jobs when none exist."""
        response = await client.get("/jobs")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    async def test_list_jobs_with_data(
        self,
        client: AsyncClient,
        sample_job_description: str,
    ):
        """Test listing jobs after analysis."""
        # Create a job
        await client.post(
            "/jobs/analyze",
            json={"raw_text": sample_job_description},
        )

        # List jobs
        response = await client.get("/jobs")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 1
        assert data["total"] == 1


@pytest.mark.asyncio
class TestJobOperations:
    """Test job operations (get, delete)."""

    async def test_get_job(
        self,
        client: AsyncClient,
        sample_job_description: str,
    ):
        """Test getting a specific job."""
        # Create a job
        create_response = await client.post(
            "/jobs/analyze",
            json={"raw_text": sample_job_description},
        )
        job_id = create_response.json()["id"]

        # Get the job
        response = await client.get(f"/jobs/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == job_id

    async def test_get_nonexistent_job(self, client: AsyncClient):
        """Test getting a job that doesn't exist."""
        from uuid import uuid4

        response = await client.get(f"/jobs/{uuid4()}")

        assert response.status_code == 404

    async def test_delete_job(
        self,
        client: AsyncClient,
        sample_job_description: str,
    ):
        """Test deleting a job."""
        # Create a job
        create_response = await client.post(
            "/jobs/analyze",
            json={"raw_text": sample_job_description},
        )
        job_id = create_response.json()["id"]

        # Delete the job
        response = await client.delete(f"/jobs/{job_id}")

        assert response.status_code == 204

        # Verify it's gone
        get_response = await client.get(f"/jobs/{job_id}")
        assert get_response.status_code == 404
