#!/usr/bin/env python3
"""Backfill: re-detecta operation en filas existentes y oculta Alquiler.

Uso (desde raíz del repo, con DATABASE_URL):
  python scripts/backfill_operation_leaks.py --dry-run
  python scripts/backfill_operation_leaks.py --sources=bienesonline,cordobaprop --limit 50
  python scripts/backfill_operation_leaks.py --from-diagnose --sources=mercado_unico

Solo hace UPDATE puntual por source_url cuando la página real indica Alquiler:
  operation='Alquiler', hidden_at=now()

No borra filas. No toca Venta confirmadas.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "apps", "api"))

from app.crawler.base import detect_operation_from_signals  # noqa: E402

UA = "PropomiBackfill/1.0 (+https://propomi.lat)"

DEFAULT_SOURCES = [
    "bienesonline",
    "cordobaprop",
    "inmoclick",
    "inmoup",
    "mercado_unico",
    "mercadolibre",
    "argenprop",
    "zonaprop",
]


def fetch(url: str, timeout: int = 20) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9"})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"  FETCH_ERR {url[:90]}: {e}", file=sys.stderr)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources", default=",".join(DEFAULT_SOURCES))
    ap.add_argument("--limit", type=int, default=50)
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--from-diagnose",
        action="store_true",
        help="Solo filas con operation='Venta' (candidatos a leak)",
    )
    args = ap.parse_args()
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    db_url = os.environ.get("DATABASE_URL") or "sqlite:///./propomi.db"
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        print("sqlalchemy requerido", file=sys.stderr)
        return 1

    engine = create_engine(db_url)
    now = datetime.now(timezone.utc)
    total_hidden = 0

    with engine.begin() as conn:
        for src in sources:
            q = text(
                "SELECT id, source_url, operation FROM properties "
                "WHERE source = :src AND source_url IS NOT NULL AND source_url != '' "
                + ("AND operation = 'Venta' " if args.from_diagnose else "")
                + "AND (hidden_at IS NULL) "
                "ORDER BY last_seen_at DESC NULLS LAST LIMIT :lim"
            )
            rows = list(conn.execute(q, {"src": src, "lim": args.limit}))
            print(f"\n=== {src} === {len(rows)} filas")
            for i, (pid, url, cur_op) in enumerate(rows, 1):
                html = fetch(url)
                if html is None:
                    time.sleep(args.sleep)
                    continue
                op = detect_operation_from_signals(url=url, html=html)
                print(f"  [{i}] id={pid} cur={cur_op} detected={op}  {url[:70]}")
                if op == "Alquiler" and cur_op != "Alquiler":
                    if args.dry_run:
                        print(f"    DRY-RUN would hide id={pid}")
                    else:
                        conn.execute(
                            text(
                                "UPDATE properties SET operation='Alquiler', hidden_at=:now "
                                "WHERE id=:id"
                            ),
                            {"now": now, "id": pid},
                        )
                        print(f"    HIDDEN id={pid}")
                    total_hidden += 1
                time.sleep(args.sleep)

    print(f"\nTotal ocultados (o dry-run): {total_hidden}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
