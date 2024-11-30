import pytest
from app.services.latex_compiler import LatexCompiler

@pytest.mark.asyncio
async def test_latex_compilation():
    compiler = LatexCompiler()
    content = "\\documentclass{article}\\begin{document}Test\\end{document}"
    success, result = await compiler.compile_latex(content, "test-job")
    assert success is True
    assert result.endswith(".pdf")