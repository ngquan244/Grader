"""
FastAPI Backend for Teaching Assistant Grader
Refactored from Gradio UI to REST API
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routes import chat, upload, quiz, grading, config as config_routes
from backend.config import settings

app = FastAPI(
    title="Teaching Assistant Grader API",
    description="API cho hệ thống chấm điểm bài thi tự động với AI Agent",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])
app.include_router(quiz.router, prefix="/api/quiz", tags=["Quiz"])
app.include_router(grading.router, prefix="/api/grading", tags=["Grading"])
app.include_router(config_routes.router, prefix="/api/config", tags=["Configuration"])

# Serve static files (generated quizzes, exports)
static_path = Path(__file__).parent.parent / "quiz-gen" / "generated_quizzes"
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static/quizzes", StaticFiles(directory=str(static_path)), name="quizzes")

exports_path = Path(__file__).parent.parent / "exports"
exports_path.mkdir(parents=True, exist_ok=True)
app.mount("/static/exports", StaticFiles(directory=str(exports_path)), name="exports")


@app.get("/")
async def root():
    return {
        "message": "Teaching Assistant Grader API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
