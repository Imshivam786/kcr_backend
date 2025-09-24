# routers/analysis.py
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pathlib import Path
from config import settings
from preprocessing.enhance import *
from fastapi.responses import JSONResponse
from ocr.reader import read_image_numpy, analyse_image
from utils.files import secure_path
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger("uvicorn.error")
UPLOAD_DIR = settings.UPLOAD_PATH

# Response models (optional)
from pydantic import BaseModel

class WordItem(BaseModel):
    region_text: str
    region_confidence: float

class EnhancedWordAnalysis(BaseModel):
    filename: str
    enhanced_image: str
    regions: List[WordItem]

class CharItem(BaseModel):
    character: str
    confidence: float

@router.get("/list_images", response_model=List[str])
async def list_images():
    files = [p.name for p in sorted(UPLOAD_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)]
    return files

@router.delete("/delete/{filename}")
async def delete_image(filename: str):
    target = secure_path(UPLOAD_DIR, filename)
    if not target.exists():
        raise HTTPException(status_code=404, detail="File not found")
    target.unlink()
    return {"status": "deleted", "filename": filename}

@router.get("/word_analyse_with_image", response_model=List[EnhancedWordAnalysis])
async def word_analyse_with_image(
    filename: Optional[str] = Query(None),
    do_deskew: bool = Query(True),
    apply_threshold: bool = Query(False),
):
    results: List[dict] = []
    targets = [secure_path(UPLOAD_DIR, filename)] if filename else list(UPLOAD_DIR.iterdir())

    loop = asyncio.get_running_loop()

    for file in targets:
        if not file.exists():
            continue

        try:
            # read file bytes async
            file_bytes = await read_file_bytes(str(file))

            enhanced_img: np.ndarray = await loop.run_in_executor(
                None,
                preprocess_for_ocr,
                file_bytes,
                do_deskew,
                apply_threshold,
            )
            data_uri = encode_image_to_data_uri(enhanced_img, ext=".png")

            try:
                ocr_out = await analyse_image(str(file))
            except Exception as e:
                logger.error(f"OCR failed for {file}: {e}")
                ocr_out = []

            regions: List[WordItem] = []
            for i, (bbox, text, confidence) in enumerate(ocr_out):
                txt = text if text is not None else ""
                conf = float(confidence) if confidence is not None else 0.0
                regions.append(WordItem(region_text=txt, region_confidence=conf))

            results.append(
                EnhancedWordAnalysis(
                    filename=file.name,
                    enhanced_image=data_uri,
                    regions=regions,
                ).dict()
            )

        except Exception as exc:
            logger.exception(f"Processing failed for {file}: {exc}")
            continue

    return JSONResponse(content=results)

@router.get("/char_analyse", response_model=List[CharItem])
async def char_analyse(filename: Optional[str] = Query(None)):
    results = []
    targets = [secure_path(UPLOAD_DIR, filename)] if filename else list(UPLOAD_DIR.iterdir())
    
    for file in targets:
        if not file.exists():
            continue
        try:
            ocr_out = await analyse_image(str(file))
        except Exception as e:
            logger.error(f"OCR failed for {file}: {e}")
            continue
            
        for item in ocr_out:
            # item is [bbox, text, confidence]
            text = item[1] if len(item) > 1 else ""
            conf = float(item[2]) if len(item) > 2 and item[2] is not None else 0.0
           
            for ch in list(text):
                results.append({"character": ch, "confidence": conf})
    
    return results
