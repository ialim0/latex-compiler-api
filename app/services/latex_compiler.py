from __future__ import annotations
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import tempfile
from typing import Tuple, Optional
from functools import cached_property
import boto3
from botocore.config import Config

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

class S3Storage:
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
            config=Config(signature_version='s3v4')
        )
        self.bucket_name = settings.AWS_BUCKET_NAME

    async def upload_file(self, file_path: Path, key: str) -> str:
        """Upload a file to S3 and return its URL"""
        try:
            await asyncio.to_thread(
                self.s3_client.upload_file,
                str(file_path),
                self.bucket_name,
                key
            )
            
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            return url
        except Exception as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise

class LatexCompiler:
    def __init__(self, max_workers: int = None):
        self.executor = ThreadPoolExecutor(max_workers=max_workers or settings.MAX_COMPILER_WORKERS)
        self.cache = RedisCache()
        self.semaphore = asyncio.Semaphore(max_workers or settings.MAX_COMPILER_WORKERS)
        self.s3_storage = S3Storage()

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
            
            s3_key = f"cvs/{job.job_id}.pdf"
            s3_url = await self.s3_storage.upload_file(job.pdf_file, s3_key)
            
            return True, s3_url