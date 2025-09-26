import os
import re
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

# =========================
#  Configuración Tesseract
# =========================
# Intenta detectar Tesseract en Windows; si no, usa el que esté en PATH
POSSIBLE_TESS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
for p in POSSIBLE_TESS:
    if Path(p).is_file():
        pytesseract.pytesseract.tesseract_cmd = p
        # Si está instalado, también configuramos tessdata
        tessdata = Path(p).parent / "tessdata"
        if tessdata.is_dir():
            os.environ["TESSDATA_PREFIX"] = str(tessdata)
        break  # encontrado

# =========================
#  Carpetas de entrada (RELATIVAS)
# =========================
BASE_DIR = Path(__file__).resolve().parent
CARPETA_FACTURAS       = BASE_DIR / "PruebaFacturas"
CARPETA_CALIFICACIONES = BASE_DIR / "PruebaCalificaciones"

# =========================
#  OCR settings
# =========================
OCR_LANG   = "eng+spa"
OCR_CONFIG = "--oem 3 --psm 6"

# Palabras clave de TOTAL más amplias (facturas)
TOTAL_PATTERNS = (
    "TOTAL", "Total", "Amount Due", "AMOUNT DUE", "Grand Total", "GRAND TOTAL",
    "Importe Total", "IMPORTE TOTAL", "Total a pagar", "TOTAL A PAGAR"
)

# =========================
#  Utilidades comunes
# =========================
def preprocesar_imagen(ruta: Path):
    """Aplica filtros para mejorar la lectura OCR."""
    img = Image.open(ruta).convert("L")
    w, h = img.size
    if max(w, h) < 1600:
        img = img.resize((int(w * 1.6), int(h * 1.6)), Image.LANCZOS)
    img = ImageEnhance.Contrast(img).enhance(1.6)
    img = ImageEnhance.Sharpness(img).enhance(1.2)
    img = ImageOps.autocontrast(img)
    img = img.filter(ImageFilter.MedianFilter(size=3))
    return img

def extraer_texto(ruta: Path) -> str:
    """Ejecuta OCR sobre la imagen dada."""
    img = preprocesar_imagen(ruta)
    return pytesseract.image_to_string(img, lang=OCR_LANG, config=OCR_CONFIG)

def _normaliza_num(s: str):
    """Convierte '1.234,56' o '1,234.56' a float 1234.56 si es posible."""
    s = s.strip().replace(" ", "")
    if not s:
        return None
    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        if "," in s and s.count(",") == 1:
            s = s.replace(",", ".")
        elif s.count(".") > 1:
            parts = s.split(".")
            s = "".join(parts[:-1]) + "." + parts[-1]
    try:
        return float(s)
    except ValueError:
        return None

# =========================
#  BLOQUE FACTURAS
# =========================
def buscar_montos(texto: str):
    """Encuentra valores numéricos con formato de dinero."""
    patron = r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})|\d+(?:[.,]\d{2})"
    brutos = re.findall(patron, texto)
    vistos = set()
    montos = []
    for b in brutos:
        val = _normaliza_num(b)
        if val is None:
            continue
        if val not in vistos:
            vistos.add(val)
            montos.append(val)
    montos.sort()
    return montos

def _hay_total(texto: str) -> bool:
    t = texto.upper()
    return any(p.upper() in t for p in TOTAL_PATTERNS)

def procesar_factura(ruta: Path):
    """Procesa una factura e imprime resultados."""
    try:
        texto = extraer_texto(ruta).strip()

        print(f"\n📑 Analizando FACTURA: {ruta.name}")
        print("-" * 72)

        montos = buscar_montos(texto)

        if _hay_total(texto) and montos:
            print("✔️ Se localizó una referencia a TOTAL junto con valores.")
            vista = ", ".join(f"{m:,.2f}" for m in montos[:15])
            print("💰 Cantidades (normalizadas):", vista + (" ..." if len(montos) > 15 else ""))
            print(f"🧮 Candidato a Total (mayor detectado): {montos[-1]:,.2f}")
        elif montos:
            print("ℹ️ Se identificaron cifras numéricas, pero no aparece una palabra de TOTAL.")
            print("💰 Cantidades (normalizadas):", ", ".join(f"{m:,.2f}" for m in montos[:15]))
        else:
            print("⚠️ No se hallaron montos ni referencias a un total.")

    except Exception as e:
        print(f"❌ Ocurrió un problema procesando {ruta}: {e}")

def correr_facturas():
    print("\n🔎 Revisando imágenes de FACTURAS en:", CARPETA_FACTURAS)
    if not CARPETA_FACTURAS.is_dir():
        print("🚫 La carpeta de FACTURAS no existe junto al script. Crea 'PruebaFacturas' y pon tus imágenes allí.")
        return

    archivos = [p for p in CARPETA_FACTURAS.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
    if not archivos:
        print("🚫 No se encontraron imágenes de facturas.")
        return

    for ruta in archivos:
        procesar_factura(ruta)


    print("\n🔎 Revisando imágenes de CALIFICACIONES en:", CARPETA_CALIFICACIONES)
    if not CARPETA_CALIFICACIONES.is_dir():
        print("🚫 La carpeta de CALIFICACIONES no existe junto al script. Crea 'PruebaCalificaciones' y pon tus imágenes allí.")
        return

    archivos = [p for p in CARPETA_CALIFICACIONES.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")]
    if not archivos:
        print("🚫 No se encontraron imágenes de calificaciones.")
        return

    

# =========================
#  MAIN
# =========================
def main():
    print(f"📂 Base: {BASE_DIR}")
    correr_facturas()
    

if __name__ == "__main__":
    main()
