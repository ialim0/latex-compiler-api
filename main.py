from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import tempfile
import os
import subprocess
from pathlib import Path
import shutil
import uuid
from typing import Optional, Dict, Union

app = FastAPI()

class LatexRequest(BaseModel):
    content: str

class LatexResponse(BaseModel):
    status: str
    result: Union[str, Dict[str, str]]  # Either URL or error logs

class LatexCompiler:
    def __init__(self, output_dir: str = "pdf_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def compile_latex(self, content: str) -> tuple[bool, str]:
        # Create a temporary directory for compilation
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Write the LaTeX content to a temporary file
            tex_file = temp_dir_path / "document.tex"
            tex_file.write_text(content)
            
            try:
                # Run pdflatex twice to resolve references
                for _ in range(2):
                    process = subprocess.run(
                        ["pdflatex", "-interaction=nonstopmode", tex_file.name],
                        cwd=temp_dir,
                        capture_output=True,
                        text=True
                    )
                
                if process.returncode != 0:
                    return False, process.stdout + process.stderr
                
                # Generate unique filename for the PDF
                pdf_filename = f"{uuid.uuid4()}.pdf"
                pdf_path = self.output_dir / pdf_filename
                
                # Move the generated PDF to the output directory
                shutil.move(temp_dir_path / "document.pdf", pdf_path)
                
                return True, pdf_filename
                
            except Exception as e:
                return False, str(e)

# Initialize the LaTeX compiler
latex_compiler = LatexCompiler()

@app.post("/compile", response_model=LatexResponse)
async def compile_latex(request: LatexRequest):
    success, result = latex_compiler.compile_latex(request.content)
    
    if success:
        # Construct the URL for the PDF
        pdf_url = f"/pdf/{result}"
        return LatexResponse(
            status="success",
            result=pdf_url
        )
    else:
        return LatexResponse(
            status="error",
            result={"error": result}
        )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Serve static files (PDFs)
from fastapi.staticfiles import StaticFiles
app.mount("/pdf", StaticFiles(directory="pdf_output"), name="pdf")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)