# ocr/reader.py
import easyocr
from typing import Optional
import logging
from starlette.concurrency import run_in_threadpool
import numpy as np
# from cnn.recognize_character import recognize

logger = logging.getLogger("uvicorn.error")
_reader: Optional[easyocr.Reader] = None

def init_reader(lang_list=["kn"], gpu: bool = False):
    global _reader
    if _reader is None:
        logger.info(f"Loading the Model for OCR")
        _reader = easyocr.Reader(lang_list, gpu=gpu) 
    return _reader

def shutdown_reader():
    global _reader
    _reader = None

async def read_image_numpy(np_image: np.ndarray, detail: int = 1):
    if _reader is None:
        raise RuntimeError("OCR reader is not initialized. Call init_reader first.")
    # call reader.readtext in threadpool
    return await run_in_threadpool(_reader.readtext, np_image, detail)

async def analyse_image(image_path):
    if _reader is None:
        raise RuntimeError("OCR reader is not initialized. Call init_reader first.")
    # recognize characters
    # try:
    #     _readers_regions = recognize(image_path)
    # except:
    #     logger.info(f"Going ahead with the fallback condition")
    #     return _reader.readtext(image_path,
    #                      text_threshold=0.3,
    #                      low_text=0.2,
    #                      link_threshold=0.2,
    #                      width_ths=0.5,
    #                      height_ths=0.5,
    #                      mag_ratio=2.0,
    #                      canvas_size=2560,
    #                      detail=1)

    return _reader.readtext(image_path,
                         text_threshold=0.3,
                         low_text=0.2,
                         link_threshold=0.2,
                         width_ths=0.5,
                         height_ths=0.5,
                         mag_ratio=2.0,
                         canvas_size=2560,
                         detail=1)
