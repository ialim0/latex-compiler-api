import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = "/home/alim/Personnal/gzendocs/core-zendoc"
STORAGE_DIR = os.path.join(BASE_DIR, "storage")

def compile_latex(content: str, job_id: str):
    logger.info(f"Starting compilation for job {job_id}")
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
        logger.error(f"Compilation failed for job {job_id}")
        with open(f"{job_dir}/error.log", "w") as f:
            f.write(result.stdout)
            f.write(result.stderr)
    else:
        logger.info(f"Compilation successful for job {job_id}")
        os.rename(f"{job_dir}/input.pdf", f"{STORAGE_DIR}/{job_id}.pdf")
        for file in os.listdir(job_dir):
            os.remove(f"{job_dir}/{file}")
        os.rmdir(job_dir)

    logger.info(f"Compilation process completed for job {job_id}")
