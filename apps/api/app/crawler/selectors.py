"""Selectores por fuente. Verificar contra HTML real antes de producción.

Caballito / CABA — placeholders basados en patrones típicos de portales AR.
No scrapean detrás de login ni usan credenciales.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    id: str
    name: str
    base_url: str
    list_path: str
    # CSS / patrones — ajustar tras test_parsers con HTML real
    card: str = "div.postingCard, article.card, div.listing-card"
    title: str = "h2, h3, .postingCard-title, .card-title"
    price: str = ".price, .postingCard-price, [data-qa='POSTING_CARD_PRICE']"
    location: str = ".location, .postingCard-location, [data-qa='POSTING_CARD_LOCATION']"
    link: str = "a[href]"
    surface: str = ".surface, [data-qa='POSTING_CARD_DESCRIPTION']"
    rooms: str = ".rooms"
    image: str = "img"
    # Query de zona piloto
    default_query: str = "caballito"
    notes: str = ""


SOURCES: dict[str, SourceConfig] = {
    "zonaprop": SourceConfig(
        id="zonaprop",
        name="ZonaProp",
        base_url="https://www.zonaprop.com.ar",
        list_path="/departamentos-venta-caballito.html",
        notes="Selectores orientativos — validar con HTML real antes de cron prod.",
    ),
    "argenprop": SourceConfig(
        id="argenprop",
        name="Argenprop",
        base_url="https://www.argenprop.com",
        list_path="/departamento-venta-barrio-caballito",
        notes="Selectores orientativos — validar con HTML real antes de cron prod.",
    ),
}
