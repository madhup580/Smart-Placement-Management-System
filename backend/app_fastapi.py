"""
FastAPI Application Entry Point
Replaces Flask app.py for interview routes
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import existing Flask app for other routes (hybrid approach)
# Or create new FastAPI routes
from interview_fastapi import router as interview_router

app = FastAPI(
    title="Interview Preparation Platform API",
    description="AI Virtual Interview System with FastAPI",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include interview router
app.include_router(interview_router)

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Interview Preparation Platform API",
        "version": "2.0.0"
    }

@app.get("/api")
async def api_info():
    return {
        "status": "ok",
        "message": "Interview Preparation Platform API",
        "endpoints": {
            "interview": "/api/v1/interview/start, /api/v1/interview/submit-answer"
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "app_fastapi:app",
        host="0.0.0.0",
        port=5000,
        reload=True
    )
