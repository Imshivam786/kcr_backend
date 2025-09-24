# backend/preprocessing/enhance.py
import cv2
import numpy as np
from typing import Tuple
import logging
import base64
import aiofiles

logger = logging.getLogger("uvicorn.error")

def bytes_to_cv2_image(file_bytes: bytes) -> np.ndarray:
    """
        Decode raw image bytes into an OpenCV BGR image.
    """
    arr = np.frombuffer(file_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image bytes to OpenCV image.")
    return img

def denoise_and_grayscale(img: np.ndarray) -> np.ndarray:
    """
        Convert a BGR image to grayscale and reduce salt-and-pepper noise.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.medianBlur(gray, 3)
    return blurred

def enhance_contrast(img_gray: np.ndarray) -> np.ndarray:
    """
        Improve local contrast of a grayscale image.
    """
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    return clahe.apply(img_gray)

def threshold_image(img_gray: np.ndarray) -> np.ndarray:
    """
        Convert grayscale image to binary.
    """
    _, th = cv2.threshold(img_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return th

def morphological_clean(img_bin: np.ndarray) -> np.ndarray:
    """
        Remove small isolated noise and small artifacts in a binary image (clean it up).
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2,2))
    opened = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernel)
    return opened

def deskew_image(img_gray: np.ndarray) -> np.ndarray:
    """
        Estimate the global skew angle of the image text/foreground and rotate image to make text horizontal.
    """
    coords = np.column_stack(np.where(img_gray < 255))
    if coords.size == 0:
        return img_gray
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = img_gray.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img_gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    logger.debug(f"Deskew angle: {angle:.2f}")
    return rotated

def preprocess_for_ocr(file_bytes: bytes, do_deskew: bool = True, apply_threshold: bool = False) -> np.ndarray:
    """
    Produce an image suitable for OCR:
      - returns BGR color if apply_threshold=False
      - returns binary image (single channel) if apply_threshold=True (for segmentation)
    """
    img = bytes_to_cv2_image(file_bytes)  # BGR
    h, w = img.shape[:2]
    max_side = max(h, w)
    if max_side > 1600:
        scale = 1600.0 / float(max_side)
        img = cv2.resize(img, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.medianBlur(l, 3)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    limg = cv2.merge((l, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    gray = cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY)
    if do_deskew:
        gray = deskew_image(gray)
        enhanced = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    if apply_threshold:
        _, th = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        clean = morphological_clean(th)
        return clean
    return enhanced


async def read_file_bytes(path: str) -> bytes:
    async with aiofiles.open(path, "rb") as f:
        return await f.read()

def encode_image_to_data_uri(img: np.ndarray, ext: str = ".png") -> str:
    success, buf = cv2.imencode(ext, img)
    if not success:
        raise RuntimeError("Failed to encode image with cv2.imencode")
    b = buf.tobytes()
    b64 = base64.b64encode(b).decode("ascii")
    mime = "image/png" if ext.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


