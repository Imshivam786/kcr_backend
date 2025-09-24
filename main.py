from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import logging

from config import settings  # new import

logger = logging.getLogger("uvicorn.error")

app = FastAPI(title="KCR Backend")

# CORS using settings
origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ensure upload dir exists
UPLOAD_DIR = settings.UPLOAD_PATH
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# mount static files
from fastapi.staticfiles import StaticFiles
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# include routers (routers import config, not main)
from routers import upload, analysis
app.include_router(upload.router, prefix="", tags=["upload"])
app.include_router(analysis.router, prefix="", tags=["analysis"])

from ocr.reader import init_reader, shutdown_reader

@app.on_event("startup")
async def startup_event():
    logger.info("Initializing OCR reader...")
    init_reader(gpu=settings.MODEL_USE_GPU)

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down OCR reader...")
    shutdown_reader()
