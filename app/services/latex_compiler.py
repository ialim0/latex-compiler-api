import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import subprocess
import shutil
from typing import Tuple
from enum import Enum

from app.core.exceptions import LatexCompilationError
from app.services.cache import RedisCache
from app.config import settings

logger = logging.getLogger(__name__)

class CompilerType(Enum):
    PDFLATEX = "pdflatex"
    XELATEX = "xelatex"

class LatexCompiler:
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=settings.MAX_COMPILER_WORKERS)
        self.cache = RedisCache()

    def _detect_compiler_type(self, content: str) -> CompilerType:
        """Detect whether to use XeLaTeX based on content analysis."""
        if any(pattern in content for pattern in [
            "\\usepackage{fontspec}",
            "\\setmainfont",
            "\\newfontfamily",
            "\\usepackage{xeCJK}",
            "\\usepackage{unicode-math}"
        ]):
            return CompilerType.XELATEX
        
        return CompilerType.PDFLATEX

    def _needs_bibtex(self, content: str) -> bool:
        """Check if the document needs bibliography processing."""
        return any(pattern in content for pattern in [
            "\\bibliography{",
            "\\bibliographystyle{",
            "\\cite{"
        ])

    async def compile_latex(self, content: str, job_id: str) -> Tuple[bool, str]:
        cache_key = f"latex:{hash(content)}"
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for job {job_id}")
            return True, cached_result.decode() if isinstance(cached_result, bytes) else cached_result

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._compile_in_thread,
                content,
                job_id
            )
            
            if result[0]:
                await self.cache.set(cache_key, result[1])
            
            return result
        except Exception as e:
            logger.error(f"Compilation error for job {job_id}: {str(e)}")
            raise LatexCompilationError(str(e))

    def _compile_in_thread(self, content: str, job_id: str) -> Tuple[bool, str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            tex_file = temp_dir_path / "document.tex"
            tex_file.write_text(content)
            
            compiler_type = self._detect_compiler_type(content)
            needs_bibtex = self._needs_bibtex(content)
            
            logger.info(f"Using {compiler_type.value} for job {job_id}")
            
            try:
                self._run_compiler(compiler_type, tex_file, temp_dir_path)

                if needs_bibtex:
                    self._run_bibtex(tex_file, temp_dir_path)
                    self._run_compiler(compiler_type, tex_file, temp_dir_path)
                    self._run_compiler(compiler_type, tex_file, temp_dir_path)
                else:
                    self._run_compiler(compiler_type, tex_file, temp_dir_path)

                pdf_filename = f"{job_id}.pdf"
                pdf_path = self.output_dir / pdf_filename
                
                shutil.move(temp_dir_path / "document.pdf", pdf_path)
                
                return True, pdf_filename
            
            except subprocess.TimeoutExpired:
                logger.error(f"Compilation timed out for job {job_id}")
                raise LatexCompilationError("Compilation timed out")
            except Exception as e:
                logger.error(f"Unexpected error during compilation: {str(e)}")
                raise LatexCompilationError(f"Compilation failed: {str(e)}")

    def _run_compiler(self, compiler_type: CompilerType, tex_file: Path, output_dir: Path):
        """Run the LaTeX compiler with appropriate options."""
        cmd = [
            compiler_type.value,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory", str(output_dir),
            str(tex_file)
        ]
        
        process = subprocess.run(
            cmd,
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=settings.COMPILATION_TIMEOUT
        )
        
        if process.returncode != 0:
            logger.error(f"{compiler_type.value} compilation error: {process.stdout + process.stderr}")
            raise LatexCompilationError(process.stdout + process.stderr)

    def _run_bibtex(self, tex_file: Path, output_dir: Path):
        """Run BibTeX for bibliography processing."""
        process = subprocess.run(
            ["bibtex", tex_file.stem],
            cwd=output_dir,
            capture_output=True,
            text=True,
            timeout=settings.COMPILATION_TIMEOUT
        )
        
        if process.returncode != 0:
            logger.error(f"BibTeX error: {process.stdout + process.stderr}")
            raise LatexCompilationError(process.stdout + process.stderr)