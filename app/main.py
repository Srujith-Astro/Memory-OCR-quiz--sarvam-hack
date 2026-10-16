import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import UPLOADS_DIR
from app.database import init_db
from app.routes import router

# Initialize database
init_db()

app = FastAPI(
    title="MemoryRecall - Gamified Active Recall & Spaced Repetition",
    description="Full-stack learning application powered by Sarvam AI",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)

# Mount uploads directory
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Mount static files
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def read_root():
    return FileResponse(str(STATIC_DIR / "index.html"))

@app.get("/health")
def health():
    return {"status": "ok", "app": "MemoryRecall", "sarvam_ai": "ready"}

@app.get("/download-pdf")
def download_pdf():
    pdf_path = Path(__file__).resolve().parent.parent / "MemoryRecall_Project_Documentation.pdf"
    if pdf_path.exists():
        return FileResponse(str(pdf_path), media_type="application/pdf", filename="MemoryRecall_Project_Documentation.pdf")
    return {"error": "PDF not generated yet"}

