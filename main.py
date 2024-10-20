from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import os
import uuid
import redis
from rq import Queue

app = FastAPI()

BASE_DIR = "/home/alim/Personnal/gzendocs/core-zendoc"
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True) 

redis_conn = redis.Redis(host='localhost', port=6379, db=0)
queue = Queue(connection=redis_conn)

class LatexRequest(BaseModel):
    content: str

def compile_latex(content: str, job_id: str):
    job_dir = f"/tmp/{job_id}"
    os.makedirs(job_dir, exist_ok=True)
    
    with open(f"{job_dir}/input.tex", "w") as f:
        f.write(content)
    
    result = subprocess.run(
        ["pdflatex", "-output-directory", job_dir, f"{job_dir}/input.tex"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        with open(f"{job_dir}/error.log", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)
    else:
        os.rename(f"{job_dir}/input.pdf", f"{STORAGE_DIR}/{job_id}.pdf")
    
    for file in os.listdir(job_dir):
        os.remove(f"{job_dir}/{file}")
    os.rmdir(job_dir)

@app.post("/compile")
async def compile_latex_endpoint(request: LatexRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    
    cached_pdf = redis_conn.get(request.content)
    if cached_pdf:
        return {"job_id": job_id, "status": "completed", "pdf_url": f"/pdf/{cached_pdf.decode()}"}
    
    queue.enqueue(compile_latex, request.content, job_id)
    
    return {"job_id": job_id, "status": "queued"}

@app.get("/status/{job_id}")
async def job_status(job_id: str):
    if os.path.exists(f"{STORAGE_DIR}/{job_id}.pdf"):
        return {"status": "completed", "pdf_url": f"/pdf/{job_id}"}
    elif os.path.exists(f"/tmp/{job_id}/error.log"):
        with open(f"/tmp/{job_id}/error.log", "r") as f:
            error_log = f.read()
        return {"status": "failed", "error_log": error_log}
    else:
        return {"status": "in_progress"}

@app.get("/pdf/{job_id}")
async def get_pdf(job_id: str):
    pdf_path = f"{STORAGE_DIR}/{job_id}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf")
    else:
        raise HTTPException(status_code=404, detail="PDF not found")
