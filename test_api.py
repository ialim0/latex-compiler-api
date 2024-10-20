import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
import os
import uuid
from fastapi import Response
from main import app, STORAGE_DIR
from worker import compile_latex
from fastapi.responses import FileResponse

client = TestClient(app)

@pytest.fixture
def mock_redis(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("main.redis_client", mock)
    return mock

@pytest.fixture
def mock_celery_task(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("main.compile_latex", mock)
    return mock

@pytest.fixture
def mock_async_result(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr("main.AsyncResult", mock)
    return mock

class MockFileResponse(FileResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stat_result = os.stat_result((0,) * 10)

    async def __call__(self, *args, **kwargs):
        await super().__call__(*args, **kwargs)
        return Response(content="Mocked PDF content", media_type="application/pdf")

def test_compile_latex_endpoint_new_job(mock_redis, mock_celery_task):
    mock_redis.get.return_value = None
    mock_celery_task.delay.return_value.id = "test_job_id"

    response = client.post("/compile", json={"content": "Test LaTeX content"})

    assert response.status_code == 200
    assert response.json() == {"job_id": "test_job_id", "status": "queued"}
    mock_celery_task.delay.assert_called_once()

def test_compile_latex_endpoint_cached(mock_redis):
    mock_redis.get.return_value = b"cached_job_id"

    response = client.post("/compile", json={"content": "Cached LaTeX content"})

    assert response.status_code == 200
    response_json = response.json()
    assert "job_id" in response_json
    assert isinstance(uuid.UUID(response_json["job_id"]), uuid.UUID)
    assert response_json["status"] == "completed"
    assert response_json["pdf_url"] == "/pdf/cached_job_id"

def test_job_status_completed(mock_async_result):
    job_id = "completed_job_id"
    mock_async_result.return_value.state = 'SUCCESS'

    with patch("os.path.exists", return_value=True):
        response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json() == {"status": "completed", "pdf_url": f"/pdf/{job_id}"}

def test_job_status_failed_with_log(mock_async_result):
    job_id = "failed_job_id"
    mock_async_result.return_value.state = 'FAILURE'

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data="Error log content")):
        response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json() == {"status": "failed", "error_log": "Error log content"}

def test_job_status_in_progress(mock_async_result):
    job_id = "in_progress_job_id"
    mock_async_result.return_value.state = 'PENDING'

    response = client.get(f"/status/{job_id}")

    assert response.status_code == 200
    assert response.json() == {"status": "in_progress"}

def test_get_pdf_success():
    job_id = "existing_pdf_job_id"
    pdf_path = f"{STORAGE_DIR}/{job_id}.pdf"
    
    # Create a mock PDF file for testing
    with open(pdf_path, 'w') as f:
        f.write("%PDF-1.4 mock PDF content")  # Minimal valid PDF content
    
    # Create a mock FileResponse
    mock_file_response = MockFileResponse(pdf_path, media_type="application/pdf")
    
    with patch("os.path.exists", return_value=True), \
         patch("main.FileResponse", return_value=mock_file_response) as mock_file_response_class:
        response = client.get(f"/pdf/{job_id}")
    
    assert response.status_code == 200

def test_get_pdf_not_found():
    job_id = "non_existing_pdf_job_id"

    with patch("os.path.exists", return_value=False):
        response = client.get(f"/pdf/{job_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": "PDF not found"}

def test_compile_latex_task():
    job_id = "test_compile_job_id"
    content = "Test LaTeX Content"

    with patch("subprocess.run") as mock_run, \
         patch("os.rename") as mock_rename, \
         patch("os.remove") as mock_remove, \
         patch("os.rmdir") as mock_rmdir:

        mock_run.return_value.returncode = 0

        result = compile_latex(content, job_id)

    assert result == job_id
    mock_run.assert_called_once()
    mock_rename.assert_called_once()
    assert mock_remove.call_count > 0
    mock_rmdir.assert_called_once()

def test_compile_latex_task_failure():
    job_id = "test_compile_fail_job_id"
    content = "Test LaTeX Content"

    with patch("subprocess.run") as mock_run, \
         patch("builtins.open", mock_open()) as mock_file:

        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "Compilation error output"
        mock_run.return_value.stderr = "Compilation error log"

        with pytest.raises(Exception, match="LaTeX compilation failed"):
            compile_latex(content, job_id)

    mock_run.assert_called_once()
    mock_file.assert_any_call(f"/tmp/{job_id}/input.tex", "w")
    mock_file.assert_any_call(f"/tmp/{job_id}/error.log", "w")
    mock_file().write.assert_any_call("Compilation error output")
    mock_file().write.assert_any_call("Compilation error log")
