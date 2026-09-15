"""Configuración por fuente: dominio, generador de URLs de listado, y si
el robots.txt ya fue verificado manualmente (curl) antes de habilitarla.

IMPORTANTE: `enabled=False` hasta confirmar robots.txt con curl manual
(ver tarea 4 del roadmap). run_crawl() salta las fuentes no habilitadas.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator

from . import queries


@dataclass
class SourceConfig:
    id: str
    name: str
    base_url: str
    list_urls_fn: Callable[[], Iterator[str]]
    enabled: bool = False
    robots_note: str = ""


SOURCES: dict[str, SourceConfig] = {
    "cordobaprop": SourceConfig(
        id="cordobaprop",
        name="CordobaProp",
        base_url="https://cordobaprop.com",
        list_urls_fn=queries.cordobaprop_list_urls,
        enabled=True,
        robots_note="Confirmado 2026-09-14: Allow: / (solo bloquea /admin/ /api/ /sdk/ /content/). Sitemap disponible.",
    ),
    "zonaprop": SourceConfig(
        id="zonaprop",
        name="ZonaProp",
        base_url="https://www.zonaprop.com.ar",
        list_urls_fn=queries.zonaprop_list_urls,
        enabled=False,
        robots_note="Pendiente: confirmar robots.txt con curl manual antes de habilitar.",
    ),
    "argenprop": SourceConfig(
        id="argenprop",
        name="Argenprop",
        base_url="https://www.argenprop.com",
        list_urls_fn=queries.argenprop_list_urls,
        enabled=False,
        robots_note="Pendiente: confirmar robots.txt con curl manual antes de habilitar.",
    ),
    "mendozaprop": SourceConfig(
        id="mendozaprop",
        name="MendozaProp",
        base_url="https://www.mendozaprop.com",
        list_urls_fn=queries.mendozaprop_list_urls,
        enabled=False,
        robots_note="Pendiente: confirmar robots.txt con curl manual antes de habilitar.",
    ),
    "mercado_unico": SourceConfig(
        id="mercado_unico",
        name="Mercado Único",
        base_url="https://www.mercado-unico.com",
        list_urls_fn=queries.mercado_unico_list_urls,
        enabled=False,
        robots_note="Dominio corregido a mercado-unico.com (con guión, sin .ar) — pendiente confirmar robots.txt.",
    ),
    "mercadolibre": SourceConfig(
        id="mercadolibre",
        name="Mercado Libre Inmuebles",
        base_url="https://inmuebles.mercadolibre.com.ar",
        list_urls_fn=lambda: iter([]),  # TODO: agregar generador de listado en queries.py
        enabled=False,
        robots_note="Pendiente: ML suele tener robots.txt restrictivo y anti-bot fuerte — validar antes de invertir tiempo acá.",
    ),
    "properati": SourceConfig(
        id="properati",
        name="Properati",
        base_url="https://www.properati.com.ar",
        list_urls_fn=lambda: iter([]),  # TODO: agregar generador de listado en queries.py
        enabled=False,
        robots_note="Pendiente: confirmar robots.txt con curl manual antes de habilitar.",
    ),
}
