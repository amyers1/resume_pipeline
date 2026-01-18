"""
Comprehensive test suite for the improved Resume Pipeline API.

Run with: pytest test_api_improved.py -v
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import the app - adjust import path as needed
from api_improved import ErrorCode, HealthStatus, app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_jobs_dir(tmp_path):
    """Create a temporary jobs directory."""
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()
    return jobs_dir


@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "job_data": {
            "job_details": {
                "company": "Test Corp",
                "job_title": "Senior Engineer",
                "employment_type": "Full-time",
            },
            "benefits": {
                "listed_benefits": ["Health Insurance", "401k"],
                "benefits_text": "Comprehensive benefits package",
            },
            "job_description": {
                "headline": "Join our amazing team",
                "short_summary": "We need talented engineers",
                "full_text": "This is a test job description that is long enough to pass validation requirements.",
                "must_have_skills": ["Python", "Docker", "AWS"],
                "nice_to_have_skills": ["Kubernetes", "Terraform"],
            },
        },
        "career_profile_path": "career_profile.json",
        "template": "awesome-cv",
        "output_backend": "weasyprint",
        "priority": 5,
        "enable_uploads": True,
    }


@pytest.fixture
def mock_career_profile(tmp_path):
    """Create a mock career profile file."""
    profile = tmp_path / "career_profile.json"
    profile.write_text(json.dumps({"name": "Test User", "email": "test@example.com"}))
    return profile


# ============================================================================
# ROOT ENDPOINT TESTS
# ============================================================================


def test_root_endpoint(client):
    """Test the root endpoint returns API info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert data["version"] == "1.0.0"


def test_root_has_request_id(client):
    """Test that root endpoint includes request ID in headers."""
    response = client.get("/")
    assert "X-Request-ID" in response.headers


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


def test_health_check_structure(client):
    """Test health check returns proper structure."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Check required fields
    assert "status" in data
    assert "timestamp" in data
    assert "checks" in data
    assert "version" in data

    # Check status is valid enum value
    assert data["status"] in ["healthy", "degraded", "unhealthy"]


@patch("api_improved.pika.BlockingConnection")
def test_health_check_rabbitmq_failure(mock_connection, client):
    """Test health check handles RabbitMQ failure gracefully."""
    mock_connection.side_effect = Exception("Connection failed")

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    # Should report RabbitMQ as unhealthy
    assert data["checks"]["rabbitmq"] == False
    # Overall status should be degraded or unhealthy
    assert data["status"] in ["degraded", "unhealthy"]


def test_readiness_check_healthy(client):
    """Test readiness check when healthy."""
    with patch("api_improved.health_check") as mock_health:
        mock_health.return_value = MagicMock(status=HealthStatus.HEALTHY)
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"ready": True}


def test_readiness_check_unhealthy(client):
    """Test readiness check when unhealthy."""
    with patch("api_improved.health_check") as mock_health:
        mock_health.return_value = MagicMock(status=HealthStatus.UNHEALTHY)
        response = client.get("/ready")
        assert response.status_code == 503


# ============================================================================
# JOB LISTING TESTS
# ============================================================================


def test_list_jobs_empty(client, tmp_path, monkeypatch):
    """Test listing jobs when directory is empty."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    response = client.get("/jobs")
    assert response.status_code == 200
    data = response.json()

    assert data["jobs"] == []
    assert data["total_count"] == 0
    assert data["page"] == 1
    assert data["total_pages"] == 0


def test_list_jobs_pagination(client, tmp_path, monkeypatch):
    """Test job listing pagination."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create 25 test jobs
    for i in range(25):
        job_file = jobs_dir / f"job_{i}.json"
        job_file.write_text(
            json.dumps(
                {
                    "job_details": {
                        "company": f"Company {i}",
                        "job_title": f"Position {i}",
                    }
                }
            )
        )

    # Test first page
    response = client.get("/jobs?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 10
    assert data["total_count"] == 25
    assert data["total_pages"] == 3
    assert data["page"] == 1

    # Test second page
    response = client.get("/jobs?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 10
    assert data["page"] == 2

    # Test last page
    response = client.get("/jobs?page=3&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert len(data["jobs"]) == 5
    assert data["page"] == 3


def test_list_jobs_filtering(client, tmp_path, monkeypatch):
    """Test job listing with company filter."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create jobs for different companies
    companies = ["Acme Corp", "Acme Corp", "Test Inc", "Test Inc"]
    for i, company in enumerate(companies):
        job_file = jobs_dir / f"job_{i}.json"
        job_file.write_text(
            json.dumps(
                {"job_details": {"company": company, "job_title": f"Position {i}"}}
            )
        )

    # Filter by Acme Corp
    response = client.get("/jobs?company=Acme+Corp")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] == 2
    assert all(job["company"] == "Acme Corp" for job in data["jobs"])


def test_list_jobs_sorting(client, tmp_path, monkeypatch):
    """Test job listing with sorting."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create jobs with different companies
    companies = ["Zebra Inc", "Apple Corp", "Microsoft"]
    for i, company in enumerate(companies):
        job_file = jobs_dir / f"job_{i}.json"
        job_file.write_text(
            json.dumps(
                {"job_details": {"company": company, "job_title": f"Position {i}"}}
            )
        )

    # Sort by company ascending
    response = client.get("/jobs?sort_by=company&sort_order=asc")
    assert response.status_code == 200
    data = response.json()
    companies_returned = [job["company"] for job in data["jobs"]]
    assert companies_returned == ["Apple Corp", "Microsoft", "Zebra Inc"]


def test_list_jobs_invalid_page(client, tmp_path, monkeypatch):
    """Test listing jobs with invalid page number."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create one job
    job_file = jobs_dir / "job_1.json"
    job_file.write_text(
        json.dumps({"job_details": {"company": "Test", "job_title": "Position"}})
    )

    # Request page 999
    response = client.get("/jobs?page=999&page_size=10")
    assert response.status_code == 400


# ============================================================================
# JOB SUBMISSION TESTS
# ============================================================================


@patch("api_improved.publish_job_request")
def test_submit_job_success(
    mock_publish, client, sample_job_data, tmp_path, monkeypatch
):
    """Test successful job submission."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Mock successful publish
    mock_publish.return_value = "job-123"

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 201
    data = response.json()

    assert "job_id" in data
    assert "status_url" in data
    assert "created_at" in data
    assert data["message"] == "Job submitted successfully"

    # Verify job file was created
    assert len(list(jobs_dir.glob("api-job-*.json"))) == 1


def test_submit_job_missing_company(client, sample_job_data, tmp_path, monkeypatch):
    """Test job submission with missing company name."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Remove company
    sample_job_data["job_data"]["job_details"]["company"] = None

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422  # Pydantic validation error


def test_submit_job_missing_job_title(client, sample_job_data, tmp_path, monkeypatch):
    """Test job submission with missing job title."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Remove job title
    sample_job_data["job_data"]["job_details"]["job_title"] = None

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422


def test_submit_job_invalid_career_profile(
    client, sample_job_data, tmp_path, monkeypatch
):
    """Test job submission with non-existent career profile."""
    monkeypatch.chdir(tmp_path)

    sample_job_data["career_profile_path"] = "nonexistent.json"

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422
    data = response.json()
    assert "career_profile_path" in str(data).lower()


def test_submit_job_invalid_template(client, sample_job_data, tmp_path, monkeypatch):
    """Test job submission with invalid template."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    sample_job_data["template"] = "invalid-template"

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422


def test_submit_job_invalid_backend(client, sample_job_data, tmp_path, monkeypatch):
    """Test job submission with invalid backend."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    sample_job_data["output_backend"] = "invalid-backend"

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422


def test_submit_job_short_description(client, sample_job_data, tmp_path, monkeypatch):
    """Test job submission with too short description."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    sample_job_data["job_data"]["job_description"]["full_text"] = "Too short"

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 400
    data = response.json()
    assert data["error_code"] == ErrorCode.VALIDATION_ERROR


@patch("api_improved.publish_job_request")
def test_submit_job_rabbitmq_failure(
    mock_publish, client, sample_job_data, tmp_path, monkeypatch
):
    """Test job submission when RabbitMQ fails."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Mock RabbitMQ failure
    import pika.exceptions

    mock_publish.side_effect = pika.exceptions.AMQPConnectionError("Connection failed")

    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 503
    data = response.json()
    assert data["error_code"] == ErrorCode.QUEUE_ERROR

    # Verify job file was cleaned up
    assert len(list(jobs_dir.glob("api-job-*.json"))) == 0


def test_submit_job_priority_validation(client, sample_job_data, tmp_path, monkeypatch):
    """Test job submission with invalid priority."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Test priority too high
    sample_job_data["priority"] = 11
    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422

    # Test priority too low
    sample_job_data["priority"] = -1
    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 422


# ============================================================================
# JOB RESUBMISSION TESTS
# ============================================================================


@patch("api_improved.publish_job_request")
def test_resubmit_job_success(mock_publish, client, tmp_path, monkeypatch):
    """Test successful job resubmission."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Create existing job file
    job_id = "existing-job"
    job_file = jobs_dir / f"{job_id}.json"
    job_file.write_text(
        json.dumps({"job_details": {"company": "Test", "job_title": "Engineer"}})
    )

    mock_publish.return_value = "job-456"

    response = client.post(
        f"/jobs/{job_id}/submit",
        json={
            "career_profile_path": "career_profile.json",
            "template": "awesome-cv",
            "output_backend": "weasyprint",
            "priority": 5,
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert "status_url" in data


def test_resubmit_nonexistent_job(client, tmp_path, monkeypatch):
    """Test resubmitting a job that doesn't exist."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    response = client.post(
        "/jobs/nonexistent-job/submit",
        json={"career_profile_path": "career_profile.json", "template": "awesome-cv"},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == ErrorCode.JOB_NOT_FOUND


def test_resubmit_invalid_job_id(client, tmp_path, monkeypatch):
    """Test resubmitting with invalid job ID format."""
    monkeypatch.chdir(tmp_path)

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    # Job ID with directory traversal attempt
    response = client.post(
        "/jobs/../etc/passwd/submit",
        json={"career_profile_path": "career_profile.json"},
    )

    assert response.status_code == 400


# ============================================================================
# ERROR RESPONSE TESTS
# ============================================================================


def test_error_response_structure(client):
    """Test that error responses have consistent structure."""
    # Trigger a 404 error
    response = client.post("/jobs/nonexistent/submit", json={})

    assert response.status_code in [400, 404, 422]  # Various error codes
    data = response.json()

    # All errors should have these fields
    if "error_code" in data:  # Custom error response
        assert "message" in data
        assert "timestamp" in data


def test_request_id_in_error(client):
    """Test that errors include request ID."""
    response = client.get("/nonexistent")
    assert response.status_code == 404

    # Request ID should be in headers
    assert "X-Request-ID" in response.headers


# ============================================================================
# CORS TESTS
# ============================================================================


def test_cors_headers(client):
    """Test CORS headers are present."""
    response = client.options(
        "/jobs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers


# ============================================================================
# SSE TESTS (Basic)
# ============================================================================


def test_sse_endpoint_exists(client):
    """Test that SSE endpoints exist."""
    # Just check the endpoint exists, don't test streaming
    # Full SSE testing requires more complex setup

    # This will fail to connect to RabbitMQ but endpoint should exist
    response = client.get("/jobs/status")
    # SSE endpoints return special responses, just verify they don't 404
    assert response.status_code != 404


def test_sse_job_specific_endpoint(client):
    """Test job-specific SSE endpoint exists."""
    response = client.get("/jobs/test-job-id/status")
    assert response.status_code != 404


# ============================================================================
# VALIDATION TESTS
# ============================================================================


def test_path_traversal_prevention(client, tmp_path, monkeypatch):
    """Test that path traversal is prevented."""
    monkeypatch.chdir(tmp_path)

    malicious_paths = [
        "../../../etc/passwd",
        "../../sensitive_file.json",
        "/etc/passwd",
    ]

    for path in malicious_paths:
        sample_data = {
            "job_data": {
                "job_details": {"company": "Test", "job_title": "Engineer"},
                "benefits": {},
                "job_description": {
                    "full_text": "Test description that is long enough"
                },
            },
            "career_profile_path": path,
        }

        response = client.post("/jobs", json=sample_data)
        assert response.status_code in [400, 422]  # Should be rejected


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


@patch("api_improved.publish_job_request")
def test_full_job_submission_workflow(
    mock_publish, client, sample_job_data, tmp_path, monkeypatch
):
def test_full_job_submission_workflow(mock_publish, client, sample_job_data, tmp_path, monkeypatch):
    """Test complete job submission workflow."""
    monkeypatch.chdir(tmp_path)
    jobs_dir = tmp_path / "jobs"
    jobs_dir.mkdir()

    # Create mock career profile
    profile = tmp_path / "career_profile.json"
    profile.write_text('{"name": "Test"}')

    mock_publish.return_value = "workflow-job-123"

    # 1. Submit job
    response = client.post("/jobs", json=sample_job_data)
    assert response.status_code == 201
    job_id = response.json()["job_id"]

    # 2. List jobs (should include new job)
    response = client.get("/jobs")
    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert any(job["job_id"].startswith("api-job-") for job in jobs)

    # 3. Check health
    response = client.get("/health")
    assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
