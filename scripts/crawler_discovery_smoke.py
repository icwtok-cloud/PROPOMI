#!/usr/bin/env python3
"""Smoke de discovery: para cada fuente enabled=True, pide la 1ª list_url
y corre extract_detail_urls. Solo lectura HTTP, sin DB.

Uso (desde apps/api o con PYTHONPATH):
  cd apps/api && PYTHONPATH=. python ../../scripts/crawler_discovery_smoke.py
  # o filtrar:
  PYTHONPATH=. python ../../scripts/crawler_discovery_smoke.py mercadolibre_mx argencasas
"""
from __future__ import annotations

import sys
import time

# Permitir import desde apps/api
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.crawler.selectors import SOURCES  # type: ignore
from app.crawler.links import extract_detail_urls  # type: ignore
from app.crawler.runner import fetch  # type: ignore


FOCUS = {
    "argencasas",
    "bullano",
    "departamentosenpozo",
    "grupoedisur",
    "mercadolibre_mx",
}


def main(argv: list[str]) -> int:
    only = set(argv[1:]) if len(argv) > 1 else None
    rows = []
    for sid, cfg in SOURCES.items():
        if not cfg.enabled:
            continue
        if only and sid not in only:
            continue
        try:
            urls = list(cfg.list_urls_fn() or [])
        except Exception as exc:
            rows.append((sid, "list_urls_error", 0, str(exc)[:120]))
            continue
        if not urls:
            rows.append((sid, "no_list_urls", 0, ""))
            continue
        list_url = urls[0]
        try:
            html = fetch(list_url)
            found = extract_detail_urls(sid, html, cfg.base_url, limit=50)
            rows.append((sid, list_url[:80], len(found), "FOCUS" if sid in FOCUS else ""))
        except Exception as exc:
            rows.append((sid, list_url[:80], -1, str(exc)[:120]))
        time.sleep(1.2)

    print(f"{'source':<22} {'detail_urls':>11}  note")
    print("-" * 72)
    for sid, url_or_status, n, note in rows:
        mark = " << FOCUS" if sid in FOCUS else ""
        print(f"{sid:<22} {n:>11}  {note}{mark}")
        if n <= 0:
            print(f"  → {url_or_status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
