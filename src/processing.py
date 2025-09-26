import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

# ----------------- Regex de importes -----------------
MONEY_2DEC  = re.compile(r"(?<!\w)(?:€\s*)?(?:\d{1,3}(?:[.,]\d{3})*|\d+)[.,]\d{2}(?:\s*€)?(?!\w)")
MONEY_23DEC = re.compile(r"(?<!\w)(?:€\s*)?(?:\d{1,3}(?:[.,]\d{3})*|\d+)[.,]\d{2,3}(?:\s*€)?(?!\w)")

# ----------------- Patrones de pie -------------------
PAT_TOTAL = re.compile(r"\btotal\b", re.I)
PAT_SUBT  = re.compile(r"\b(?:base\s+imponible|subtotal)\b", re.I)
# Tolerante: IVA/LVA/1VA/(VA/lVA/!VA
PAT_IVA   = re.compile(r"[^\w]?([il1]va|\(?va)\b", re.I)
# % como 21% o 21,0%
PCT_RE    = re.compile(r"\b([0-9]{1,2})(?:[.,][0-9]+)?\s*%\b")

# Inicio de tabla
PAT_TABLE_START = re.compile(r"\bCONCEPTO\b", re.I)
# Palabras clave de ítems (tu lógica 1)
ITEM_KEYWORDS = ("Curso", "Dron", "Casco")

@dataclass
class OcrResult:
    file: str
    text: str
    numbers: list[float]        # precios unitarios
    sum: float
    avg: Optional[float]
    total_line: Optional[float]
    subtotal_line: Optional[float]
    iva_line: Optional[float]

# ----------------- Helpers -----------------

def _clean_num(tok: str) -> float:
    t = tok.replace("€", "").replace(" ", "").strip()
    # Si trae 3 decimales, recorta a 2 (20.666 -> 20.66)
    m = re.search(r"^(.+?)[.,](\d{2,3})$", t)
    if m and len(m.group(2)) == 3:
        t = f"{m.group(1)}.{m.group(2)[:2]}"
    if "," in t and "." in t:
        # 1.234,56 -> 1234.56
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            # 1,234.56 -> 1234.56
            t = t.replace(",", "")
    else:
        t = t.replace(",", ".")
    return float(t)

def _first_amount(s: str, money_re=MONEY_23DEC) -> Optional[float]:
    m = money_re.search(s)
    return _clean_num(m.group(0)) if m else None

def _all_amounts(s: str, money_re=MONEY_23DEC) -> List[float]:
    return [_clean_num(m.group(0)) for m in money_re.finditer(s)]

def _find_last_amount(lines: List[str], pat: re.Pattern) -> Optional[float]:
    """Busca bottom-up en el PIE; misma línea o hasta dos líneas debajo; rescata números pegados."""
    for i in range(len(lines)-1, -1, -1):
        ln = lines[i]
        if not pat.search(ln):
            continue
        for j in (0, 1, 2):
            k = i + j
            if k < len(lines):
                v = _first_amount(lines[k], MONEY_23DEC)
                if v is not None:
                    return v
        m2 = re.search(r"\b(\d{3,6})\b", ln.replace(" ", ""))
        if m2:
            raw = m2.group(1)
            return float(raw[:-2] + "." + raw[-2:])
    return None

def _footer_start_idx(lines: List[str]) -> int:
    for i in range(len(lines)-1, -1, -1):
        if PAT_SUBT.search(lines[i]):
            return i
    return len(lines)

def _table_start_idx(lines: List[str]) -> int:
    for i, ln in enumerate(lines):
        if PAT_TABLE_START.search(ln):
            return i
    return 0

# ----------------- Main -----------------

def analyze_text(filename: str, text: str) -> OcrResult:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Delimitar regiones
    i_table  = _table_start_idx(lines)
    i_footer = _footer_start_idx(lines)
    table_lines = lines[i_table:i_footer]
    foot_lines  = lines[i_footer:]

    # ---- PIE: subtotal, IVA, total (lógica 2) ----
    subtotal = _find_last_amount(foot_lines, PAT_SUBT)
    iva      = _find_last_amount(foot_lines, PAT_IVA)
    total    = _find_last_amount(foot_lines, PAT_TOTAL)

    # % si aparece (preferir pie)
    pct = None
    for ln in reversed(foot_lines or lines):
        m = PCT_RE.search(ln)
        if m:
            pct = float(m.group(1)); break

    if pct is not None and subtotal is not None:
        iva_calc = round(subtotal * pct / 100.0, 2)
        if iva is None or abs(iva - iva_calc) > 0.01:
            iva = iva_calc
    if subtotal is not None and iva is not None:
        total_calc = round(subtotal + iva, 2)
        if total is None or abs(total - total_calc) > 0.01:
            total = total_calc

    # ---- PRECIOS UNITARIOS: tu lógica 1 sobre la tabla ----
    unit_prices: List[float] = []

    for ln in table_lines:
        # Sólo filas de ítems reconocibles
        if any(k in ln for k in ITEM_KEYWORDS):
            amts = _all_amounts(ln, MONEY_23DEC)
            if amts:
                # el primer importe de la fila suele ser el PRECIO unitario
                price = amts[0]
                # filtrar valores razonables (evitar totales de la misma fila)
                if 0 < price < 1000:
                    unit_prices.append(price)

    # Deduplicar consecutivos (a veces OCR duplica líneas)
    dedup: List[float] = []
    for v in unit_prices:
        if not dedup or abs(dedup[-1] - v) > 1e-9:
            dedup.append(v)
    unit_prices = dedup

    s = sum(unit_prices) if unit_prices else 0.0
    avg = (s / len(unit_prices)) if unit_prices else None

    # Redondeos
    if total is not None:    total = round(total, 2)
    if subtotal is not None: subtotal = round(subtotal, 2)
    if iva is not None:      iva = round(iva, 2)

    return OcrResult(
        file=filename,
        text=text,
        numbers=unit_prices,
        sum=s,
        avg=avg,
        total_line=total,
        subtotal_line=subtotal,
        iva_line=iva,
    )

def check_value(observed: Optional[float], expected: Optional[float], tol: float) -> Dict[str, Any]:
    if observed is None or expected is None:
        return {"ok": None, "diff": None}
    diff = observed - expected
    return {"ok": abs(diff) <= tol, "diff": diff}
