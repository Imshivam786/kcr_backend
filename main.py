# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from config import settings
from database import init_db
from ocr.reader import init_reader  # Add this import

# Import routers
from routers import cases, analysis, upload

app = FastAPI(title="Kannada OCR API")

# Initialize database and OCR reader on startup
@app.on_event("startup")
def startup_event():
    init_db()
    print("✓ Database initialized")
    
    # Initialize OCR reader
    init_reader(gpu=settings.MODEL_USE_GPU)
    print("✓ OCR reader initialized")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cases.router)  # New case-based endpoints
app.include_router(analysis.router, prefix="/legacy")  # Keep old endpoints for backward compatibility
app.include_router(upload.router, prefix="/legacy")  # Keep old upload for backward compatibility

# Mount uploads directory for serving files (legacy support)
app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_PATH)), name="uploads")

@app.get("/")
def read_root():
    return {"message": "Kannada OCR API", "version": "2.0"}
