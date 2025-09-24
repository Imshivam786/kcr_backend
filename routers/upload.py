# routers/upload.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import aiofiles
from utils.files import unique_filename, secure_path
from config import settings

UPLOAD_DIR = settings.UPLOAD_PATH

router = APIRouter()

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    # generate unique filename
    fname = unique_filename(file.filename)
    dest = secure_path(UPLOAD_DIR, fname)
    try:
        async with aiofiles.open(dest, "wb") as out_file:
            content = await file.read()  # read whole file
            await out_file.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")
    finally:
        await file.close()
    return {"filename": fname}
