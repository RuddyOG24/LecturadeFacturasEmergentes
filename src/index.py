import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from config import settings
from utilsImage import load_image, preprocess, to_png_bytes, list_images
from processing import analyze_text, check_value
from ocr_providers.tesseract import configure as tess_configure, ocr_image_bytes as tess_ocr

def main():
    parser = argparse.ArgumentParser(description="OCR por lote (Tesseract) + verificación.")
    parser.add_argument("--input",  default=settings.INPUT_DIR,  help="Carpeta con imágenes")
    parser.add_argument("--output", default=str(Path(settings.OUTPUT_DIR) / "resultado.csv"),
                        help="Ruta CSV de salida")
    parser.add_argument("--expected-sum", type=float, default=None, help="Valor esperado del TOTAL")
    parser.add_argument("--expected-avg", type=float, default=None, help="Valor esperado del promedio")
    parser.add_argument("--tol", type=float, default=0.01, help="Tolerancia")
    parser.add_argument("--no-gray", action="store_true", help="Desactivar escala de grises")
    parser.add_argument("--no-binary", action="store_true", help="Desactivar umbral binario")
    parser.add_argument("--blur", action="store_true", help="Activar blur gaussiano")
    args = parser.parse_args()

    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    tess_configure(settings.TESSERACT_EXE)

    files = list_images(args.input)
    if not files:
        print(f"No encontré imágenes en: {args.input}")
        return

    rows = []
    for f in tqdm(files, desc="OCR"):
        img = load_image(str(f))
        proc = preprocess(img, grayscale=not args.no_gray, thresh_binary=not args.no_binary, blur=args.blur)
        text = tess_ocr(to_png_bytes(proc))

        res = analyze_text(f.name, text)

        # coherencia matemática: total ≈ subtotal + iva
        if res.total_line is not None and res.subtotal_line is not None and res.iva_line is not None:
            math_diff = round(res.total_line - (res.subtotal_line + res.iva_line), 2)
            math_ok = abs(math_diff) <= args.tol
        else:
            math_diff = None
            math_ok = None

        rows.append({
            "file": res.file,
            "n_numbers": len(res.numbers),
            "avg": res.avg,
            "total_line": res.total_line,
            "subtotal_line": res.subtotal_line,
            "iva_line": res.iva_line,
            "check_math_ok": math_ok,
            "check_math_diff": math_diff,
            "text": res.text
        })

    df = pd.DataFrame(rows)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\nListo → {out}")

if __name__ == "__main__":
    main()
