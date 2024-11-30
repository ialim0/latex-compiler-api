# app/services/latex_compiler.py

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import subprocess
import shutil
from typing import Tuple
import hashlib

from app.core.exceptions import LatexCompilationError
from app.services.cache import RedisCache
from app.config import settings

logger = logging.getLogger(__name__)

class LatexCompiler:
    _executor = ThreadPoolExecutor(max_workers=settings.MAX_COMPILER_WORKERS)
    _semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_COMPILATIONS)
    
    def __init__(self):
        self.output_dir = Path(settings.OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.cache = RedisCache()
        self._active_tasks = 0 
        
    @property
    def executor(self):
        return self._executor
    
    @property
    def active_workers(self):
        return self._active_tasks
        
    async def compile_latex(self, content: str, job_id: str) -> Tuple[bool, str]:
        cache_key = f"latex:{hashlib.sha256(content.encode()).hexdigest()}"
        
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for job {job_id}")
            return True, cached_result
        
        async with self._semaphore:
            self._active_tasks += 1
            try:
                result = await asyncio.get_event_loop().run_in_executor(
                    self._executor,
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
            finally:
                self._active_tasks -= 1
    
    def _compile_in_thread(self, content: str, job_id: str) -> Tuple[bool, str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            tex_file = temp_dir_path / "document.tex"
            tex_file.write_text(content)
            
            try:
                process = subprocess.run(
                    ["pdflatex", "-interaction=nonstopmode", tex_file.name],
                    cwd=temp_dir,
                    capture_output=True,
                    text=True,
                    timeout=settings.COMPILATION_TIMEOUT
                )
                
                if process.returncode != 0:
                    raise LatexCompilationError(process.stdout + process.stderr)
    
                pdf_filename = f"{job_id}.pdf"
                pdf_path = self.output_dir / pdf_filename
                
                shutil.move(temp_dir_path / "document.pdf", pdf_path)
                
                return True, pdf_filename
            
            except subprocess.TimeoutExpired:
                raise LatexCompilationError("Compilation timed out")
            except Exception as e:
                raise LatexCompilationError(str(e))
