from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
from celery.result import AsyncResult
from worker import compile_latex
import redis

app = FastAPI()
BASE_DIR = "/home/alim/Personnal/gzendocs/core-zendoc"
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

redis_client = redis.Redis(host='localhost', port=6379, db=0)

class LatexRequest(BaseModel):
    content: str

@app.post("/compile")
async def compile_latex_endpoint(request: LatexRequest):
    job_id = str(uuid.uuid4())
    cached_pdf = redis_client.get(request.content)
    if cached_pdf:
        return {"job_id": job_id, "status": "completed", "pdf_url": f"/pdf/{cached_pdf.decode()}"}
    
    task = compile_latex.delay(request.content, job_id)
    return {"job_id": task.id, "status": "queued"}

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    task = AsyncResult(job_id)
    if task.state == 'SUCCESS':
        if os.path.exists(f"{STORAGE_DIR}/{job_id}.pdf"):
            return {"status": "completed", "pdf_url": f"/pdf/{job_id}"}
        else:
            return {"status": "failed", "error": "PDF not found after job completion"}
    elif task.state == 'FAILURE':
        error_log_path = f"/tmp/{job_id}/error.log"
        if os.path.exists(error_log_path):
            with open(error_log_path, "r") as f:
                error_log = f.read()
            return {"status": "failed", "error_log": error_log}
        else:
            return {"status": "failed", "error": str(task.result)}
    else:
        return {"status": "in_progress"}

@app.get("/pdf/{job_id}")
async def get_pdf(job_id: str):
    pdf_path = f"{STORAGE_DIR}/{job_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404, detail="PDF not found")