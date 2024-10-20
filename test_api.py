import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os
import redis
from rq import Queue

# Import your FastAPI app
from main import app, STORAGE_DIR, redis_conn, compile_latex, LatexRequest

client = TestClient(app)

@pytest.fixture
def mock_redis():
    with patch('main.redis_conn') as mock:
        yield mock

@pytest.fixture
def mock_queue():
    with patch('main.queue') as mock:
        yield mock

@pytest.fixture
def mock_compile_latex():
    with patch('main.compile_latex') as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_dependencies(mock_redis, mock_queue, mock_compile_latex):
    pass

def test_compile_latex_endpoint(mock_redis, mock_queue):
    mock_redis.get.return_value = None
    response = client.post("/compile", json={"content": "\\documentclass{article}\\begin{document}Test\\end{document}"})
    assert response.status_code == 200
    assert "job_id" in response.json()
    assert response.json()["status"] == "queued"
    mock_queue.enqueue.assert_called_once()

def test_compile_latex_endpoint_cached(mock_redis):
    mock_redis.get.return_value = b"cached_job_id"
    response = client.post("/compile", json={"content": "\\documentclass{article}\\begin{document}Test\\end{document}"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["pdf_url"] == "/pdf/cached_job_id"

def test_job_status_completed():
    job_id = "test_job_id"
    os.makedirs(STORAGE_DIR, exist_ok=True)
    open(f"{STORAGE_DIR}/{job_id}.pdf", "w").close()
    
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["pdf_url"] == f"/pdf/{job_id}"
    
    os.remove(f"{STORAGE_DIR}/{job_id}.pdf")

def test_job_status_failed():
    job_id = "test_job_id"
    os.makedirs(f"/tmp/{job_id}", exist_ok=True)
    with open(f"/tmp/{job_id}/error.log", "w") as f:
        f.write("Test error")
    
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    assert response.json()["error_log"] == "Test error"
    
    os.remove(f"/tmp/{job_id}/error.log")
    os.rmdir(f"/tmp/{job_id}")

def test_job_status_in_progress():
    job_id = "test_job_id"
    response = client.get(f"/status/{job_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

def test_get_pdf_success():
    job_id = "test_job_id"
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(f"{STORAGE_DIR}/{job_id}.pdf", "w") as f:
        f.write("Test PDF content")
    
    response = client.get(f"/pdf/{job_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    
    os.remove(f"{STORAGE_DIR}/{job_id}.pdf")

def test_get_pdf_not_found():
    job_id = "nonexistent_job_id"
    response = client.get(f"/pdf/{job_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "PDF not found"

@patch('main.compile_latex')
def test_compile_latex_function(mock_compile_latex):
    content = "\\documentclass{article}\\begin{document}Test\\end{document}"
    job_id = "test_job_id"
    
    # Call the compile_latex function from main, not the mocked one
    from main import compile_latex
    compile_latex(content, job_id)
    
    # Assert that the mocked function was called
    mock_compile_latex.assert_called_once_with(content, job_id)