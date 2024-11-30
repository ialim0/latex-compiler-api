import pytest
from fastapi.testclient import TestClient
from app.main import create_application

@pytest.fixture
def app():
    return create_application()

@pytest.fixture
def client(app):
    return TestClient(app)

# 12. tests/test_compiler.py
