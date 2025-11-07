# routers/cases.py
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Any, List, Optional
from pathlib import Path
import json
from datetime import datetime

from database import get_db
from models.database import Case, Image
from config import settings
from utils.files import unique_filename, secure_path
import aiofiles

router = APIRouter(prefix="/cases", tags=["cases"])
UPLOAD_DIR = settings.UPLOAD_PATH


# Response Models
from pydantic import BaseModel, validator

class CaseResponse(BaseModel):
    case_id: str
    created_at: datetime
    image_count: int
    
    class Config:
        orm_mode = True


class CasesListResponse(BaseModel):
    cases: List[CaseResponse]
    total: int
    page: int
    page_size: int


class ImageResponse(BaseModel):
    image_id: str
    filename: str
    uploaded_at: datetime
    analyzed_at: Optional[datetime] = None
    ocr_result: Optional[Any] = None  # Change from dict to Any
    
    class Config:
        orm_mode = True
    
    @validator('ocr_result', pre=True)
    def parse_ocr_result(cls, v):
        """Parse JSON string to dict if needed"""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return None
        return v


# ===== CASE ENDPOINTS =====

@router.get("", response_model=CasesListResponse)
async def get_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get paginated list of cases"""
    offset = (page - 1) * page_size
    
    cases = db.query(Case).order_by(Case.created_at.desc()).offset(offset).limit(page_size).all()
    total = db.query(Case).count()
    
    cases_data = [
        {
            "case_id": case.case_id,
            "created_at": case.created_at,
            "image_count": len(case.images)
        }
        for case in cases
    ]
    
    return {
        "cases": cases_data,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/upload")
async def create_case_with_upload(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an image and create a new case"""
    # Create new case
    new_case = Case()
    db.add(new_case)
    db.flush()  # Get the case_id
    
    # Create case-specific directory
    case_dir = UPLOAD_DIR / new_case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    fname = unique_filename(file.filename)
    file_path = case_dir / fname
    relative_path = f"{new_case.case_id}/{fname}"
    
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        await file.close()
    
    # Create image record
    new_image = Image(
        case_id=new_case.case_id,
        filename=file.filename,
        file_path=relative_path
    )
    db.add(new_image)
    
    try:
        db.commit()
        db.refresh(new_image)
    except Exception as e:
        db.rollback()
        # Clean up file if DB operation fails
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    return {
        "case_id": new_case.case_id,
        "image_id": new_image.image_id,
        "filename": file.filename
    }


@router.get("/{case_id}/images", response_model=List[ImageResponse])
async def get_case_images(case_id: str, db: Session = Depends(get_db)):
    """Get all images for a specific case"""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    images_data = []
    for img in case.images:
        ocr_data = None
        if img.ocr_result:
            try:
                ocr_data = json.loads(img.ocr_result)
            except:
                ocr_data = None
        
        images_data.append({
            "image_id": img.image_id,
            "filename": img.filename,
            "uploaded_at": img.uploaded_at,
            "analyzed_at": img.analyzed_at,
            "ocr_result": ocr_data
        })
    
    return images_data


@router.delete("/{case_id}")
async def delete_case(case_id: str, db: Session = Depends(get_db)):
    """Delete a case and all its images"""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Delete physical files
    case_dir = UPLOAD_DIR / case_id
    if case_dir.exists():
        import shutil
        shutil.rmtree(case_dir)
    
    # Delete from database (cascade will delete images)
    db.delete(case)
    db.commit()
    
    return {"status": "deleted", "case_id": case_id}


# ===== IMAGE ENDPOINTS =====

@router.post("/{case_id}/images")
async def upload_image_to_case(
    case_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an image to an existing case"""
    case = db.query(Case).filter(Case.case_id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Create case directory if it doesn't exist
    case_dir = UPLOAD_DIR / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    
    # Save file
    fname = unique_filename(file.filename)
    file_path = case_dir / fname
    relative_path = f"{case_id}/{fname}"
    
    try:
        async with aiofiles.open(file_path, "wb") as out_file:
            content = await file.read()
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        await file.close()
    
    # Create image record
    new_image = Image(
        case_id=case_id,
        filename=file.filename,
        file_path=relative_path
    )
    db.add(new_image)
    
    # Update case's updated_at
    case.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(new_image)
    except Exception as e:
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
    
    return {
        "image_id": new_image.image_id,
        "filename": file.filename,
        "case_id": case_id
    }


@router.get("/{case_id}/images/{image_id}/file")
async def get_image_file(case_id: str, image_id: str, db: Session = Depends(get_db)):
    """Serve the actual image file"""
    from fastapi.responses import FileResponse
    
    image = db.query(Image).filter(
        Image.image_id == image_id,
        Image.case_id == case_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = UPLOAD_DIR / image.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(file_path)


@router.delete("/{case_id}/images/{image_id}")
async def delete_image(case_id: str, image_id: str, db: Session = Depends(get_db)):
    """Delete an image from a case"""
    image = db.query(Image).filter(
        Image.image_id == image_id,
        Image.case_id == case_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete physical file
    file_path = UPLOAD_DIR / image.file_path
    if file_path.exists():
        file_path.unlink()
    
    # Delete from database
    db.delete(image)
    db.commit()
    
    return {"status": "deleted", "image_id": image_id}


@router.post("/{case_id}/images/{image_id}/analyze")
async def analyze_image(
    case_id: str,
    image_id: str,
    do_deskew: bool = Query(True),
    apply_threshold: bool = Query(False),
    db: Session = Depends(get_db)
):
    """Perform OCR analysis on an image and store results"""
    from preprocessing.enhance import preprocess_for_ocr, read_file_bytes, encode_image_to_data_uri
    from ocr.reader import analyse_image
    import asyncio
    import numpy as np
    import logging
    
    logger = logging.getLogger("uvicorn.error")
    
    image = db.query(Image).filter(
        Image.image_id == image_id,
        Image.case_id == case_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    file_path = UPLOAD_DIR / image.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    try:
        # Read and preprocess image (reusing existing code)
        file_bytes = await read_file_bytes(str(file_path))
        
        loop = asyncio.get_running_loop()
        enhanced_img: np.ndarray = await loop.run_in_executor(
            None,
            preprocess_for_ocr,
            file_bytes,
            do_deskew,
            apply_threshold,
        )
        data_uri = encode_image_to_data_uri(enhanced_img, ext=".png")
        
        # Perform OCR (reusing existing code)
        try:
            ocr_out = await analyse_image(str(file_path))
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            raise HTTPException(status_code=500, detail=f"OCR processing failed: {e}")
        
        # Format results
        regions = []
        for bbox, text, confidence in ocr_out:
            txt = text if text is not None else ""
            conf = float(confidence) if confidence is not None else 0.0
            regions.append({
                "region_text": txt,
                "region_confidence": conf
            })
        
        result = [{
            "filename": image.filename,
            "enhanced_image": data_uri,
            "regions": regions
        }]
        
        # Store results in database
        image.ocr_result = json.dumps(result)
        image.analyzed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(image)
        
        return {
            "status": "success",
            "image_id": image_id,
            "analyzed_at": image.analyzed_at,
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Analysis failed for {file_path}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
