from __future__ import annotations
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile
import shutil
from typing import Tuple, Optional
from functools import cached_property

from app.core.exceptions import LatexCompilationError
from app.services.cache import RedisCache
from app.config import settings

logger = logging.getLogger(__name__)

class CompilerType(Enum):
    PDFLATEX = "pdflatex"
    XELATEX = "xelatex"

@dataclass
class CompilationJob:
    content: str
    job_id: str
    compiler_type: Optional[CompilerType] = None
    needs_bibtex: bool = False
    temp_dir: Optional[Path] = None
    
    @cached_property
    def tex_file(self) -> Path:
        if not self.temp_dir:
            raise ValueError("temp_dir must be set before accessing tex_file")
        return self.temp_dir / "document.tex"
    
    @cached_property
    def pdf_file(self) -> Path:
        if not self.temp_dir:
            raise ValueError("temp_dir must be set before accessing pdf_file")
        return self.temp_dir / "document.pdf"

class CompilationStrategy:
    def __init__(self, timeout: int):
        self.timeout = timeout

    async def compile(self, job: CompilationJob) -> None:
        raise NotImplementedError

class StandardCompilationStrategy(CompilationStrategy):
    async def compile(self, job: CompilationJob) -> None:
        await self._run_compiler(job)
        await self._run_compiler(job)

    async def _run_compiler(self, job: CompilationJob) -> None:
        cmd = [
            job.compiler_type.value,
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-output-directory", str(job.temp_dir),
            str(job.tex_file)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=job.temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            if process.returncode != 0:
                raise LatexCompilationError(f"{stdout.decode()}\n{stderr.decode()}")
        except asyncio.TimeoutError:
            raise LatexCompilationError("Compilation timed out")

class BibTexCompilationStrategy(StandardCompilationStrategy):
    async def compile(self, job: CompilationJob) -> None:
        await self._run_compiler(job)
        await self._run_bibtex(job)
        await self._run_compiler(job)
        await self._run_compiler(job)

    async def _run_bibtex(self, job: CompilationJob) -> None:
        cmd = ["bibtex", job.tex_file.stem]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=job.temp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            if process.returncode != 0:
                raise LatexCompilationError(f"BibTeX error: {stdout.decode()}\n{stderr.decode()}")
        except asyncio.TimeoutError:
            raise LatexCompilationError("BibTeX processing timed out")

class LatexCompiler:
    def __init__(self, max_workers: int = None):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=max_workers or settings.MAX_COMPILER_WORKERS)
        self.cache = RedisCache()
        self.semaphore = asyncio.Semaphore(max_workers or settings.MAX_COMPILER_WORKERS)

    def _analyze_content(self, content: str) -> Tuple[CompilerType, bool]:
        needs_bibtex = any(pattern in content for pattern in [
            "\\bibliography{",
            "\\bibliographystyle{",
            "\\cite{"
        ])
        
        compiler_type = CompilerType.XELATEX if any(pattern in content for pattern in [
            "\\usepackage{fontspec}",
            "\\setmainfont",
            "\\newfontfamily",
            "\\usepackage{xeCJK}",
            "\\usepackage{unicode-math}"
        ]) else CompilerType.PDFLATEX
        
        return compiler_type, needs_bibtex

    async def compile_latex(self, content: str, job_id: str) -> Tuple[bool, str]:
        cache_key = f"latex:{hash(content)}"
        
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for job {job_id}")
            return True, cached_result.decode() if isinstance(cached_result, bytes) else cached_result

        async with self.semaphore:
            try:
                compiler_type, needs_bibtex = self._analyze_content(content)
                
                job = CompilationJob(
                    content=content,
                    job_id=job_id,
                    compiler_type=compiler_type,
                    needs_bibtex=needs_bibtex
                )
                
                result = await self._process_job(job)
                
                if result[0]:
                    await self.cache.set(cache_key, result[1])
                
                return result
                
            except Exception as e:
                logger.error(f"Compilation error for job {job_id}: {str(e)}")
                raise LatexCompilationError(str(e))

    async def _process_job(self, job: CompilationJob) -> Tuple[bool, str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            job.temp_dir = Path(temp_dir)
            job.tex_file.write_text(job.content)
            
            strategy = (BibTexCompilationStrategy if job.needs_bibtex else StandardCompilationStrategy)(
                timeout=settings.COMPILATION_TIMEOUT
            )
            
            await strategy.compile(job)
            
            pdf_filename = f"{job.job_id}.pdf"
            output_path = self.output_dir / pdf_filename
            shutil.move(job.pdf_file, output_path)
            
            return True, pdf_filename
