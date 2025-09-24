# backend/utils/files.py
from pathlib import Path
import uuid

def unique_filename(original_name: str) -> str:
    base = Path(original_name).stem
    ext = Path(original_name).suffix or ".jpg"
    return f"{base}_{uuid.uuid4().hex}{ext}"

def secure_path(upload_dir: Path, filename: str) -> Path:
    return upload_dir / Path(filename).name
