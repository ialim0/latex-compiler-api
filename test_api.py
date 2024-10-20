import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app, redis_conn, queue, STORAGE_DIR
import os
import uuid
import shutil

client = TestClient(app)

@pytest.fixture
def mock_redis(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("main.redis_conn", mock)
    return mock

@pytest.fixture
def mock_queue(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("main.queue", mock)
    return mock

@pytest.fixture(autouse=True)
def cleanup_temp_dirs():
    yield
    if os.path.exists("/tmp/test-worker-job-id"):
        shutil.rmtree("/tmp/test-worker-job-id")

def test_compile_latex_endpoint_new_job(mock_redis, mock_queue):
    mock_redis.get.return_value = None
    mock_job = MagicMock()
    mock_job.id = "test-job-id"
    mock_queue.enqueue.return_value = mock_job

    response = client.post("/compile", json={"content": "Test LaTeX content"})
    assert response.status_code == 200
    assert response.json() == {"job_id": "test-job-id", "status": "queued"}

    mock_redis.get.assert_called_once_with("Test LaTeX content")
    mock_queue.enqueue.assert_called_once()

def test_compile_latex_endpoint_cached(mock_redis):
    mock_redis.get.return_value = b"cached-job-id"

    response = client.post("/compile", json={"content": "Cached LaTeX content"})
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "completed"
    assert result["pdf_url"] == "/pdf/cached-job-id"
    try:
        uuid.UUID(result["job_id"], version=4)
    except ValueError:
        pytest.fail(f"Invalid UUID: {result['job_id']}")

    mock_redis.get.assert_called_once_with("Cached LaTeX content")

def test_job_status_completed():
    job_id = "completed-job-id"
    os.makedirs(STORAGE_DIR, exist_ok=True)
    open(f"{STORAGE_DIR}/{job_id}.pdf", "w").close()

    with patch("main.Job.fetch") as mock_fetch:
        mock_job = MagicMock()
        mock_job.is_finished = True
        mock_fetch.return_value = mock_job

        response = client.get(f"/status/{job_id}")
        assert response.status_code == 200
        assert response.json() == {"status": "completed", "pdf_url": f"/pdf/{job_id}"}

    os.remove(f"{STORAGE_DIR}/{job_id}.pdf")

def test_job_status_in_progress():
    with patch("main.Job.fetch") as mock_fetch:
        mock_job = MagicMock()
        mock_job.is_finished = False
        mock_job.is_failed = False
        mock_fetch.return_value = mock_job

        response = client.get("/status/in-progress-job-id")
        assert response.status_code == 200
        assert response.json() == {"status": "in_progress"}

def test_job_status_failed():
    with patch("main.Job.fetch") as mock_fetch:
        mock_job = MagicMock()
        mock_job.is_finished = False
        mock_job.is_failed = True
        mock_job.exc_info = "Test error message"
        mock_fetch.return_value = mock_job

        response = client.get("/status/failed-job-id")
        assert response.status_code == 200
        assert response.json() == {"status": "failed", "error": "Test error message"}

def test_get_pdf_success():
    job_id = "test-pdf-job-id"
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(f"{STORAGE_DIR}/{job_id}.pdf", "w") as f:
        f.write("Test PDF content")

    response = client.get(f"/pdf/{job_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == b"Test PDF content"

    os.remove(f"{STORAGE_DIR}/{job_id}.pdf")

def test_get_pdf_not_found():
    response = client.get("/pdf/non-existent-job-id")
    assert response.status_code == 404
    assert response.json() == {"detail": "PDF not found"}

@patch("worker.subprocess.run")
@patch("os.rename")
def test_compile_latex_worker_success(mock_rename, mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 0
    
    from worker import compile_latex
    compile_latex("Test LaTeX content", "test-worker-job-id")

    mock_rename.assert_called_once_with(
        "/tmp/test-worker-job-id/input.pdf",
        f"{STORAGE_DIR}/test-worker-job-id.pdf"
    )

@patch("worker.subprocess.run")
def test_compile_latex_worker_failure(mock_subprocess_run):
    mock_subprocess_run.return_value.returncode = 1
    mock_subprocess_run.return_value.stdout = "Test stdout"
    mock_subprocess_run.return_value.stderr = "Test stderr"

    from worker import compile_latex
    compile_latex("Test LaTeX content", "test-worker-job-id")

    error_log_path = "/tmp/test-worker-job-id/error.log"
    assert os.path.exists(error_log_path)
    with open(error_log_path, "r") as f:
        error_log = f.read()
    assert "Test stdout" in error_log
    assert "Test stderr" in error_log