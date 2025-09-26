import os
from dotenv import load_dotenv

load_dotenv()

def _as_bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "y", "on")

class Settings:
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "TESSERACT").upper()
    TESSERACT_EXE: str = os.getenv("TESSERACT_EXE", "")

    INPUT_DIR: str  = os.getenv("INPUT_DIR", "./data/input")
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "./data/output")

    GRAYSCALE: bool     = _as_bool(os.getenv("GRAYSCALE"), True)
    THRESH_BINARY: bool = _as_bool(os.getenv("THRESH_BINARY"), True)
    BLUR: bool          = _as_bool(os.getenv("BLUR"), False)

settings = Settings()
