from pathlib import Path
from typing import List
import numpy as np
import cv2

def load_image(path: str) -> np.ndarray:
    img = cv2.imread(path)
    if img is None:
        raise FileNotFoundError(f"No pude leer la imagen: {path}")
    return img

def preprocess(
    img: np.ndarray,
    grayscale: bool = True,
    thresh_binary: bool = True,
    blur: bool = False
) -> np.ndarray:
    out = img.copy()
    if grayscale:
        out = cv2.cvtColor(out, cv2.COLOR_BGR2GRAY)
    if blur:
        out = cv2.GaussianBlur(out, (3, 3), 0)
    if thresh_binary and len(out.shape) == 2:
        _, out = cv2.threshold(out, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return out

def to_png_bytes(img: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise RuntimeError("No pude codificar la imagen a PNG.")
    return buf.tobytes()

def list_images(folder: str) -> List[Path]:
    p = Path(folder)
    exts = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
    return sorted([f for f in p.glob("*") if f.suffix.lower() in exts])
