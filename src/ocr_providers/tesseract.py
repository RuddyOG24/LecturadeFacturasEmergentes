import os
import io
from PIL import Image
import pytesseract

def configure(exe_path: str | None) -> None:
    """Configura ruta a tesseract.exe si no está en PATH."""
    if exe_path and os.path.exists(exe_path):
        pytesseract.pytesseract.tesseract_cmd = exe_path

def ocr_image_bytes(img_bytes: bytes) -> str:
    """
    OCR general (sin whitelist) para que detecte etiquetas como
    'BASE IMPONIBLE', 'SUBTOTAL', 'IVA', 'TOTAL'.
    """
    img = Image.open(io.BytesIO(img_bytes))
    return pytesseract.image_to_string(
        img,
        lang="spa+eng",
        config="--oem 1 --psm 6 -c preserve_interword_spaces=1"
    )
