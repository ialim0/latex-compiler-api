from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import uuid
import redis
from rq import Queue
from rq.job import Job
from rq.exceptions import NoSuchJobError

app = FastAPI()
BASE_DIR = "/home/alim/Personnal/gzendocs/core-zendoc"
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

redis_conn = redis.Redis(host='localhost', port=6379, db=0)
queue = Queue(connection=redis_conn)

class LatexRequest(BaseModel):
    content: str

@app.post("/compile")
async def compile_latex_endpoint(request: LatexRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    cached_pdf = redis_conn.get(request.content)
    if cached_pdf:
        return {"job_id": job_id, "status": "completed", "pdf_url": f"/pdf/{cached_pdf.decode()}"}

    job = queue.enqueue('worker.compile_latex', request.content, job_id)
    return {"job_id": job.id, "status": "queued"}

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
        if job.is_finished:
            if os.path.exists(f"{STORAGE_DIR}/{job_id}.pdf"):
                return {"status": "completed", "pdf_url": f"/pdf/{job_id}"}
            else:
                return {"status": "failed", "error": "PDF not found after job completion"}
        elif job.is_failed:
            return {"status": "failed", "error": str(job.exc_info)}
        else:
            return {"status": "in_progress"}
    except NoSuchJobError:
        if os.path.exists(f"{STORAGE_DIR}/{job_id}.pdf"):
            return {"status": "completed", "pdf_url": f"/pdf/{job_id}"}
        elif os.path.exists(f"/tmp/{job_id}/error.log"):
            with open(f"/tmp/{job_id}/error.log", "r") as f:
                error_log = f.read()
            return {"status": "failed", "error_log": error_log}
        else:
            return {"status": "unknown", "error": "Job not found in queue and no output available"}

@app.get("/pdf/{job_id}")
async def get_pdf(job_id: str):
    pdf_path = f"{STORAGE_DIR}/{job_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404, detail="PDF not found")
