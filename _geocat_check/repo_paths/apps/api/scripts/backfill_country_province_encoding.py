#!/usr/bin/env python3
"""Backfill country / province / mojibake en properties existentes.

Uso (desde apps/api, con DATABASE_URL apuntando a Postgres o SQLite):

  # dry-run (solo reporta)
  python scripts/backfill_country_province_encoding.py --dry-run

  # aplicar
  python scripts/backfill_country_province_encoding.py --apply

Idempotente: re-correr no empeora filas ya corregidas.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# apps/api en path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.crawler.normalize import SOURCE_COUNTRY, fix_mojibake
from app.main import Property, engine


# Heurística best-effort de provincia desde city/zone/url (sin re-crawl)
CITY_PROVINCE_AR = {
    "córdoba": "Córdoba",
    "cordoba": "Córdoba",
    "malagueño": "Córdoba",
    "malagueno": "Córdoba",
    "villa allende": "Córdoba",
    "mendoza": "Mendoza",
    "godoy cruz": "Mendoza",
    "guaymallén": "Mendoza",
    "rosario": "Santa Fe",
    "santa fe": "Santa Fe",
    "caba": "Buenos Aires",
    "buenos aires": "Buenos Aires",
    "la plata": "Buenos Aires",
    "mar del plata": "Buenos Aires",
}
CITY_PROVINCE_PY = {
    "asunción": "Central",
    "asuncion": "Central",
    "luque": "Central",
    "ciudad del este": "Alto Paraná",
    "encarnación": "Itapúa",
}
CITY_PROVINCE_UY = {
    "montevideo": "Montevideo",
    "pando": "Canelones",
    "ciudad de la costa": "Canelones",
    "maldonado": "Maldonado",
    "punta del este": "Maldonado",
}


def infer_country(source: str | None, city: str, zone: str, url: str) -> str:
    sid = (source or "").strip()
    if sid in SOURCE_COUNTRY:
        return SOURCE_COUNTRY[sid]
    blob = f"{city} {zone} {url}".lower()
    if "infocasas.com.py" in blob or any(c in blob for c in ("asunción", "asuncion", "ciudad del este", "luque")):
        return "Paraguay"
    if "infocasas.com.uy" in blob or "montevideo" in blob or "punta del este" in blob:
        return "Uruguay"
    return "Argentina"


def infer_province(country: str, city: str, zone: str, url: str, existing: str) -> str:
    if existing and existing.strip():
        return existing.strip()
    key = (city or "").strip().lower()
    # quitar sufijos ruidosos
    key = key.replace(" departamento de ", " ").strip()
    maps = {
        "Argentina": CITY_PROVINCE_AR,
        "Paraguay": CITY_PROVINCE_PY,
        "Uruguay": CITY_PROVINCE_UY,
    }.get(country, {})
    if key in maps:
        return maps[key]
    # partial
    for k, v in maps.items():
        if k in key or key in k:
            return v
    # URL hints AR
    ul = (url or "").lower()
    if "cordoba" in ul or "córdoba" in ul:
        return "Córdoba"
    if "mendoza" in ul:
        return "Mendoza"
    if "santa-fe" in ul or "rosario" in ul:
        return "Santa Fe"
    return existing or ""


def main() -> None:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="máx filas a procesar (0=todas)")
    args = ap.parse_args()

    changed = 0
    samples: list[str] = []
    with Session(engine) as db:
        q = select(Property)
        rows = list(db.scalars(q).all())
        if args.limit:
            rows = rows[: args.limit]
        for p in rows:
            before = (p.country, p.province, p.city, p.zone, p.title)
            country = infer_country(p.source, p.city or "", p.zone or "", p.source_url or "")
            city = fix_mojibake(p.city)
            zone = fix_mojibake(p.zone)
            title = fix_mojibake(p.title)
            desc = fix_mojibake(p.description)
            province = infer_province(country, city, zone, p.source_url or "", p.province or "")

            dirty = (
                (p.country or "") != country
                or (p.province or "") != (province or "")
                or (p.city or "") != city
                or (p.zone or "") != zone
                or (p.title or "") != title
                or (p.description or "") != desc
            )
            if not dirty:
                continue
            changed += 1
            if len(samples) < 12:
                samples.append(
                    f"id={p.id} source={p.source} "
                    f"country {p.country!r}->{country!r} "
                    f"province {p.province!r}->{province!r} "
                    f"city {p.city!r}->{city!r}"
                )
            if args.apply:
                p.country = country
                p.province = province or ""
                p.city = city
                p.zone = zone
                p.title = title
                p.description = desc
        if args.apply:
            db.commit()

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] filas a cambiar: {changed} (de {len(rows) if 'rows' in dir() else '?'})")
    for s in samples:
        print("  ", s)
    if args.dry_run:
        print("Sin escritura. Re-ejecutar con --apply para persistir.")


if __name__ == "__main__":
    main()
