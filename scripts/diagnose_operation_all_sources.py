#!/usr/bin/env python3
"""Diagnóstico de operation real en filas ya cargadas — todas las fuentes.

Re-fetchea source_url de una muestra por fuente y extrae el campo real de
operación de la página (sin tocar la base).

Uso (desde raíz del repo, con DATABASE_URL si hay DB):
  python scripts/diagnose_operation_all_sources.py
  python scripts/diagnose_operation_all_sources.py --limit 30
  python scripts/diagnose_operation_all_sources.py --sources=mendozaprop,cordobaprop
  python scripts/diagnose_operation_all_sources.py --sample-only   # sin DB

Default de fuentes: las que hardcodean operation="Venta" en el parser
(más mendozaprop ya arreglado, para re-chequeo). InfoCasas se puede incluir
con --sources=infocasas_py,infocasas_uy.

No escribe en la base. Solo lista y resume.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import defaultdict
from typing import Callable
from urllib.request import Request, urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))

UA = "PropomiDiagnose/1.0 (+https://propomi.lat)"

# Fuentes que hardcodean "Venta" en el parser (o lo hacían) + mendozaprop
# para re-chequeo. InfoCasas queda fuera del default (ya lee operation_type).
DEFAULT_SOURCES = [
    "mendozaprop",
    "bienesonline",
    "cordobaprop",
    "inmoclick",
    "inmoup",
    "mercado_unico",
    "mercadolibre",
    "argenprop",
    "zonaprop",
]

# ---------------------------------------------------------------------------
# Extractores por fuente: (html, url) -> "Venta" | "Alquiler" | None
# None = no se pudo determinar (cuenta como unknown).
# Si la fuente no tiene forma clara → marcarla no_extractable a nivel fuente.
# ---------------------------------------------------------------------------


def _norm_op(text: str | None) -> str | None:
    if not text:
        return None
    t = text.strip().lower()
    if not t:
        return None
    # alquiler primero (más específico)
    if any(k in t for k in ("alquiler", "renta", "rent", "lease", "temporal")):
        return "Alquiler"
    if any(k in t for k in ("venta", "sale", "comprar", "buy", "compra")):
        return "Venta"
    return None


def _from_url(url: str) -> str | None:
    """Heurística de path/query muy usada por los portales AR/UY/PY."""
    u = (url or "").lower()
    # path segments / query
    if re.search(r"(/|\?|&|=)(alquiler|rent|renta)([/\-?]|$)", u):
        return "Alquiler"
    if re.search(r"(/|\?|&|=)(venta|sale)([/\-?]|$)", u):
        return "Venta"
    if "-en-alquiler" in u or "/alquiler-" in u or "operaciones=2" in u:
        return "Alquiler"
    if "-en-venta" in u or "/venta-" in u or "operaciones=1" in u:
        return "Venta"
    return None


def _og_title(html: str) -> str:
    m = re.search(r'property="og:title"\s+content="([^"]+)"', html, re.I)
    if m:
        return m.group(1)
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
    return m.group(1) if m else ""


def _all_ld(html: str) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            out.extend([x for x in data if isinstance(x, dict)])
        elif isinstance(data, dict):
            if "@graph" in data and isinstance(data["@graph"], list):
                out.extend([x for x in data["@graph"] if isinstance(x, dict)])
            else:
                out.append(data)
    return out


def _ld_business_function(html: str) -> str | None:
    for obj in _all_ld(html):
        bf = obj.get("businessFunction") or obj.get("additionalType") or ""
        if isinstance(bf, list):
            bf = " ".join(str(x) for x in bf)
        op = _norm_op(str(bf))
        if op:
            return op
        # Offer / RealEstateListing a veces trae category
        for key in ("category", "name", "description"):
            op = _norm_op(str(obj.get(key) or ""))
            if op:
                return op
    return None


def extract_mendozaprop(html: str, url: str) -> str | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return _from_url(url) or _norm_op(_og_title(html))
    try:
        root = json.loads(m.group(1))
    except json.JSONDecodeError:
        return _from_url(url)
    data = (root.get("props") or {}).get("pageProps", {}).get("data") or {}
    tid = data.get("transaction_type_id")
    try:
        tid = int(tid) if tid is not None else None
    except (TypeError, ValueError):
        tid = None
    # Confirmado 2026-09-17: 2=Venta, 1=Alquiler
    if tid == 2:
        return "Venta"
    if tid == 1:
        return "Alquiler"
    return _from_url(url) or _norm_op(_og_title(html))


def extract_infocasas(html: str, url: str) -> str | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        try:
            root = json.loads(m.group(1))
            data = (root.get("props") or {}).get("pageProps", {}).get("data") or {}
            ot = data.get("operation_type") or {}
            if isinstance(ot, dict) and ot.get("name"):
                op = _norm_op(str(ot["name"]))
                if op:
                    return op
        except json.JSONDecodeError:
            pass
    return _from_url(url) or _norm_op(_og_title(html))


def extract_mercadolibre(html: str, url: str) -> str | None:
    # Path es la señal más fiable en ML Inmuebles
    op = _from_url(url)
    if op:
        return op
    # JSON-LD Product / category
    op = _ld_business_function(html)
    if op:
        return op
    # melidata a veces trae category_id
    m = re.search(r'"category_id"\s*:\s*"([^"]+)"', html)
    if m:
        op = _norm_op(m.group(1))
        if op:
            return op
    return _norm_op(_og_title(html))


def extract_argenprop(html: str, url: str) -> str | None:
    op = _from_url(url)
    if op:
        return op
    # Título típico: "Departamento en Venta en Olivos..."
    title = _og_title(html)
    op = _norm_op(title)
    if op:
        return op
    return _ld_business_function(html)


def extract_zonaprop(html: str, url: str) -> str | None:
    op = _from_url(url)
    if op:
        return op
    # postings / avisoInfo embebido
    for pat in (
        r'"operationId"\s*:\s*(\d+)',
        r'"operation"\s*:\s*"([^"]+)"',
        r'"realEstateType"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"',
    ):
        m = re.search(pat, html)
        if m:
            val = m.group(1)
            if val in ("1", "2"):
                # ZP histórico: a veces 1=venta 2=alquiler — no asumir sin más señal
                pass
            op = _norm_op(val)
            if op:
                return op
    return _ld_business_function(html) or _norm_op(_og_title(html))


def extract_cordobaprop(html: str, url: str) -> str | None:
    op = _from_url(url)
    if op:
        return op
    # listados usan ?operaciones=1 (venta); fichas a veces no
    op = _ld_business_function(html)
    if op:
        return op
    return _norm_op(_og_title(html))


def extract_inmoup(html: str, url: str) -> str | None:
    # URLs: /departamentos-en-venta-en-mendoza
    op = _from_url(url)
    if op:
        return op
    return _norm_op(_og_title(html)) or _ld_business_function(html)


def extract_inmoclick(html: str, url: str) -> str | None:
    op = _from_url(url)
    if op:
        return op
    return _norm_op(_og_title(html)) or _ld_business_function(html)


def extract_mercado_unico(html: str, url: str) -> str | None:
    # window.__NUXT__ — estructura variable; buscar señales de texto
    m = re.search(r"window\.__NUXT__\s*=\s*(.*?);\s*</script>", html, re.S)
    if m:
        blob = m.group(1)
        # buscar claves típicas
        for pat in (
            r'"operacion"\s*:\s*"([^"]+)"',
            r'"operation"\s*:\s*"([^"]+)"',
            r'"tipoOperacion"\s*:\s*"([^"]+)"',
            r'"tipo_operacion"\s*:\s*"([^"]+)"',
        ):
            mm = re.search(pat, blob, re.I)
            if mm:
                op = _norm_op(mm.group(1))
                if op:
                    return op
        # texto libre en el blob
        if re.search(r"alquiler", blob, re.I) and not re.search(r"venta", blob, re.I):
            return "Alquiler"
    op = _from_url(url)
    if op:
        return op
    return _norm_op(_og_title(html))


def extract_bienesonline(html: str, url: str) -> str | None:
    op = _ld_business_function(html)
    if op:
        return op
    op = _from_url(url)
    if op:
        return op
    return _norm_op(_og_title(html))


def extract_generic(html: str, url: str) -> str | None:
    """Fallback: URL → og:title → JSON-LD."""
    return _from_url(url) or _norm_op(_og_title(html)) or _ld_business_function(html)


EXTRACTORS: dict[str, Callable[[str, str], str | None]] = {
    "mendozaprop": extract_mendozaprop,
    "infocasas_py": extract_infocasas,
    "infocasas_uy": extract_infocasas,
    "mercadolibre": extract_mercadolibre,
    "argenprop": extract_argenprop,
    "zonaprop": extract_zonaprop,
    "cordobaprop": extract_cordobaprop,
    "inmoup": extract_inmoup,
    "inmoclick": extract_inmoclick,
    "mercado_unico": extract_mercado_unico,
    "bienesonline": extract_bienesonline,
}

# Fuentes sin extractor confiable de campo de operación en página
# (se reportan no_extractable si se piden y no hay ni URL ni título usable).
# Ninguna queda bloqueada del todo: siempre hay fallback URL/title.


def fetch(url: str, timeout: int = 20) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9"})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FETCH_ERR {url[:90]}: {e}", file=sys.stderr)
        return None


def load_rows(source: str, limit: int) -> list[tuple[str, str]]:
    """Devuelve [(id, source_url), ...] desde DB o lista vacía si no hay DB."""
    rows: list[tuple[str, str]] = []
    try:
        from sqlalchemy import create_engine, text

        db_url = os.environ.get("DATABASE_URL") or "sqlite:///./propomi.db"
        engine = create_engine(db_url)
        with engine.connect() as conn:
            q = text(
                "SELECT id, source_url FROM properties "
                "WHERE source = :src AND source_url IS NOT NULL "
                "AND source_url != '' "
                "ORDER BY last_seen_at DESC "
                "LIMIT :lim"
            )
            for r in conn.execute(q, {"src": source, "lim": limit}):
                rows.append((str(r[0]), str(r[1])))
    except Exception as e:
        print(f"  [{source}] DB no disponible: {e}", file=sys.stderr)
    return rows


# Muestras públicas mínimas para --sample-only / sin DB (solo fuentes con URL conocida)
SAMPLE_URLS: dict[str, list[tuple[str, str]]] = {
    "mendozaprop": [
        ("sample-venta", "https://www.mendozaprop.com/venta-duplex-3-habitaciones-tomba-propiedades/6784734"),
        ("sample-alquiler", "https://www.mendozaprop.com/alquiler-casa-3-habitaciones-rodriguez-damonte/6778984"),
    ],
}


def diagnose_source(
    source: str,
    limit: int,
    sleep: float,
    sample_only: bool,
) -> dict[str, int | list[str]]:
    extractor = EXTRACTORS.get(source, extract_generic)
    counts: dict[str, int] = {
        "Venta": 0,
        "Alquiler": 0,
        "unknown": 0,
        "fetch_error": 0,
        "no_extractable": 0,
        "inspected": 0,
    }
    alquiler_urls: list[str] = []

    if sample_only or not os.environ.get("DATABASE_URL"):
        rows = SAMPLE_URLS.get(source, [])
        if not rows and sample_only:
            print(f"\n=== {source} === (sin muestra pública hardcodeada; saltando en --sample-only)")
            counts["no_extractable"] = 1
            return {**counts, "alquiler_urls": alquiler_urls}
    else:
        rows = []

    db_rows = load_rows(source, limit)
    if db_rows:
        rows = db_rows
        print(f"\n=== {source} === DB: {len(rows)} filas (limit={limit})")
    elif rows:
        print(f"\n=== {source} === muestra pública: {len(rows)} URLs")
    else:
        print(f"\n=== {source} === sin filas en DB ni muestra; nada que inspeccionar")
        return {**counts, "alquiler_urls": alquiler_urls}

    for i, (pid, url) in enumerate(rows, 1):
        counts["inspected"] += 1
        html = fetch(url)
        if html is None:
            counts["fetch_error"] += 1
            print(f"  [{i}/{len(rows)}] {pid} FETCH_ERR  {url[:80]}")
            time.sleep(sleep)
            continue
        try:
            op = extractor(html, url)
        except Exception as e:
            print(f"  [{i}/{len(rows)}] {pid} EXTRACT_ERR: {e}", file=sys.stderr)
            counts["unknown"] += 1
            time.sleep(sleep)
            continue
        if op == "Venta":
            counts["Venta"] += 1
        elif op == "Alquiler":
            counts["Alquiler"] += 1
            alquiler_urls.append(url)
        else:
            counts["unknown"] += 1
            op = "unknown"
        print(f"  [{i}/{len(rows)}] {pid} → {op}  {url[:80]}")
        time.sleep(sleep)

    return {**counts, "alquiler_urls": alquiler_urls}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--sources",
        default="",
        help="Lista separada por comas (default: fuentes que hardcodean Venta + mendozaprop)",
    )
    ap.add_argument("--limit", type=int, default=50, help="Máx. filas por fuente (default 50)")
    ap.add_argument("--sleep", type=float, default=0.4, help="Segundos entre requests")
    ap.add_argument(
        "--sample-only",
        action="store_true",
        help="No usar DB; solo muestras públicas hardcodeadas (mendozaprop)",
    )
    ap.add_argument(
        "--include-infocasas",
        action="store_true",
        help="Agregar infocasas_py e infocasas_uy al set default",
    )
    args = ap.parse_args()

    if args.sources.strip():
        sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    else:
        sources = list(DEFAULT_SOURCES)
        if args.include_infocasas:
            sources.extend(["infocasas_py", "infocasas_uy"])

    print("Diagnóstico de operation real (solo lectura, no escribe en DB)")
    print(f"Fuentes: {', '.join(sources)}")
    print(f"Limit por fuente: {args.limit}")

    summary: dict[str, dict] = {}
    for src in sources:
        summary[src] = diagnose_source(src, args.limit, args.sleep, args.sample_only)

    print("\n" + "=" * 60)
    print("RESUMEN CONSOLIDADO")
    print("=" * 60)
    tot = defaultdict(int)
    for src, c in summary.items():
        print(
            f"  {src:16}  inspected={c['inspected']:4}  "
            f"Venta={c['Venta']:4}  Alquiler={c['Alquiler']:4}  "
            f"unknown={c['unknown']:4}  fetch_error={c['fetch_error']:4}"
        )
        for k in ("inspected", "Venta", "Alquiler", "unknown", "fetch_error"):
            tot[k] += int(c[k])  # type: ignore[arg-type]
        urls = c.get("alquiler_urls") or []
        if urls:
            print(f"    → URLs Alquiler ({len(urls)}):")
            for u in urls[:20]:
                print(f"       {u}")
            if len(urls) > 20:
                print(f"       ... y {len(urls) - 20} más")

    print("-" * 60)
    print(
        f"  {'TOTAL':16}  inspected={tot['inspected']:4}  "
        f"Venta={tot['Venta']:4}  Alquiler={tot['Alquiler']:4}  "
        f"unknown={tot['unknown']:4}  fetch_error={tot['fetch_error']:4}"
    )

    if tot["Alquiler"]:
        print("\n⚠ Hay filas cuya página real indica Alquiler. Revisar para backfill/ocultar.")
    else:
        print("\n✓ Ninguna URL inspeccionada resultó Alquiler (o no hubo filas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
