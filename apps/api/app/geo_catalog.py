"""Catálogo geográfico exhaustivo para el formulario de alta de agencia/propiedad.

Estructura: país → provincias/departamentos → ciudades/localidades.
Generado a partir de fuentes oficiales / abiertas (ver README de la entrega).
No depende de Property (a diferencia de GET /properties/filters).

Los datos viven en apps/api/app/geo_data/{ar,py,uy}.json para no inflar
el diff de texto; este módulo solo los carga y expone get_geo_catalog().
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "geo_data"


def _load_country(code: str) -> dict[str, list[str]]:
    path = _DATA_DIR / f"{code}.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


_AR: dict[str, list[str]] = _load_country("ar")
_PY: dict[str, list[str]] = _load_country("py")
_UY: dict[str, list[str]] = _load_country("uy")

GEO_CATALOG: dict[str, dict[str, list[str]]] = {
    "Argentina": _AR,
    "Paraguay": _PY,
    "Uruguay": _UY,
}


def get_geo_catalog() -> dict:
    """Serializa el catálogo para la API: countries + provincesByCountry + citiesByProvince."""
    countries = list(GEO_CATALOG.keys())
    provinces_by_country: dict[str, list[str]] = {}
    cities_by_province: dict[str, list[str]] = {}
    for country, provinces in GEO_CATALOG.items():
        provinces_by_country[country] = sorted(provinces.keys())
        for province, cities in provinces.items():
            cities_by_province[f"{country}|{province}"] = sorted(cities)
    return {
        "countries": countries,
        "provincesByCountry": provinces_by_country,
        "citiesByProvince": cities_by_province,
    }
