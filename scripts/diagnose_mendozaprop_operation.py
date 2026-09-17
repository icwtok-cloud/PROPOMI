#!/usr/bin/env python3
"""Diagnóstico de operation real en filas mendozaprop ya cargadas.

Re-fetchea el source_url de cada fila (o una muestra) y lee
transaction_type_id del __NEXT_DATA__ sin tocar la base.

Uso:
  # desde apps/api con el venv activado y DATABASE_URL apuntando a la DB
  python scripts/diagnose_mendozaprop_operation.py [--limit N] [--sample-only]

No escribe en la base. Solo reporta conteos y lista URLs de alquiler.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen

# Permitir importar app si se corre desde raíz del repo
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))

UA = "PropomiDiagnose/1.0 (+https://propomi.lat)"


def extract_transaction_type_id(html: str) -> int | None:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    try:
        root = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    data = (root.get("props") or {}).get("pageProps", {}).get("data") or {}
    tid = data.get("transaction_type_id")
    if tid is None:
        return None
    try:
        return int(tid)
    except (TypeError, ValueError):
        return None


def fetch(url: str, timeout: int = 20) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FETCH_ERR {url}: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0, help="Máximo de filas a inspeccionar (0=todas)")
    ap.add_argument("--sample-only", action="store_true", help="Solo primeras 20 (sin DB si no hay)")
    ap.add_argument("--sleep", type=float, default=0.4, help="Segundos entre requests")
    args = ap.parse_args()

    # Intentamos leer de la DB real; si falla, modo demo con URLs hardcodeadas
    rows: list[tuple[str, str]] = []  # (id, source_url)
    try:
        from sqlalchemy import create_engine, text
        db_url = os.environ.get("DATABASE_URL") or "sqlite:///./propomi.db"
        engine = create_engine(db_url)
        with engine.connect() as conn:
            q = text(
                "SELECT id, source_url FROM properties "
                "WHERE source = 'mendozaprop' AND source_url IS NOT NULL "
                "ORDER BY last_seen_at DESC"
            )
            for r in conn.execute(q):
                rows.append((str(r[0]), str(r[1])))
        print(f"DB: {len(rows)} filas mendozaprop con source_url")
    except Exception as e:
        print(f"DB no disponible ({e}); modo muestra con URLs públicas conocidas", file=sys.stderr)
        rows = [
            ("sample-venta", "https://www.mendozaprop.com/venta-duplex-3-habitaciones-tomba-propiedades/6784734"),
            ("sample-alquiler", "https://www.mendozaprop.com/alquiler-casa-3-habitaciones-rodriguez-damonte/6778984"),
        ]

    if args.sample_only:
        rows = rows[:20]
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    counts = {"Venta": 0, "Alquiler": 0, "unknown": 0, "fetch_error": 0}
    alquiler_urls: list[str] = []

    for i, (pid, url) in enumerate(rows, 1):
        html = fetch(url)
        if html is None:
            counts["fetch_error"] += 1
            continue
        tid = extract_transaction_type_id(html)
        if tid == 2:
            counts["Venta"] += 1
            label = "Venta"
        elif tid == 1:
            counts["Alquiler"] += 1
            label = "Alquiler"
            alquiler_urls.append(url)
        else:
            counts["unknown"] += 1
            label = f"unknown(tid={tid})"
        print(f"[{i}/{len(rows)}] {pid} tid={tid} → {label}  {url[:80]}")
        time.sleep(args.sleep)

    print("\n=== RESUMEN ===")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    if alquiler_urls:
        print(f"\nURLs que en la página real son Alquiler ({len(alquiler_urls)}):")
        for u in alquiler_urls:
            print(f"  {u}")
    else:
        print("\nNinguna URL re-inspeccionada resultó Alquiler (o no hubo filas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
