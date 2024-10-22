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
import pytest
from app.services.latex_compiler import LatexCompiler

@pytest.mark.asyncio
async def test_latex_compilation():
    compiler = LatexCompiler()
    content = "\\documentclass{article}\\begin{document}Test\\end{document}"
    success, result = await compiler.compile_latex(content, "test-job")
    assert success is True
    assert result.endswith(".pdf")