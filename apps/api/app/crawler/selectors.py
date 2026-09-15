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
        # Confirmado 2026-09-15 (curl -i, 200 OK, real, no challenge de Cloudflare).
        # NO es un simple Allow: / — tiene reglas específicas:
        #   - Permite /propiedades/*-ubicado-en-* (fichas), bloquea el resto de
        #     ese patrón de URL.
        #   - Paginación limitada: solo permite página 2 a 5 (tanto
        #     *pagina-N.html como *pagina=N) — página 1 implícita, nada más allá
        #     de la 5 (coincide con el límite de "máx. 3 páginas de listado por
        #     corrida" que ya tiene runner.py, así que estamos dentro).
        #   - Bloquea /develop/ /mails/ /errores/ /bloques/ /bumex/ /cms/
        #     /panel/ /ecommerce/ /static/ /publica-tu-propiedad/ /zp/ /tracking/.
        #   - Bloquea cualquier URL con utm_*, n_src=, gad_source=, gclid=,
        #     fbclid=, duplicated=true, labs= como query param.
        # Sigue en enabled=False: falta la tarea 13 (validar queries.py/links.py
        # contra HTML real de listado para respetar estos patrones antes de
        # habilitar) — el robots.txt en sí ya no es el bloqueante.
        robots_note="Confirmado 2026-09-15: robots.txt permite fichas /propiedades/*-ubicado-en-* y páginas 2-5. queries.py apuntado a Caballito-venta y links.py filtra ese patrón. BLOQUEADO 2026-09-15: listados/fichas devuelven Cloudflare challenge (403 cf-mitigated: challenge) — no viable sin anti-bot. enabled=False hasta decisión de producto.",
    ),
    "argenprop": SourceConfig(
        id="argenprop",
        name="Argenprop",
        base_url="https://www.argenprop.com",
        list_urls_fn=queries.argenprop_list_urls,
        enabled=False,
        # Confirmado 2026-09-15: ni siquiera se pudo obtener el robots.txt —
        # CloudFront devolvió 403 "Request blocked" directo. Bot protection a
        # nivel de borde, antes de llegar a la app. No hay robots.txt que
        # confirmar porque el request ni pasa; probablemente tampoco vamos a
        # poder crawlear fichas reales sin una solución de proxy/anti-bot
        # dedicada (fuera de alcance por ahora).
        robots_note="2026-09-15: 403 Forbidden (CloudFront) incluso para /robots.txt — bot protection en el borde, no confirmable con curl simple. Evaluar más adelante si vale la pena invertir en bypass; por ahora no habilitar.",
    ),
    "mendozaprop": SourceConfig(
        id="mendozaprop",
        name="MendozaProp",
        base_url="https://www.mendozaprop.com",
        list_urls_fn=queries.mendozaprop_list_urls,
        enabled=False,
        # Confirmado 2026-09-15: /robots.txt devuelve 404 (la propia página de
        # error 404 de Next.js del sitio, no un bloqueo de borde) — es decir,
        # el sitio no publica un robots.txt. Por el estándar (RFC 9309),
        # ausencia de robots.txt = no hay restricciones declaradas. Queda
        # limpio del lado de robots.txt; falta la tarea 13 (validar
        # queries.py/links.py contra HTML real) antes de habilitar.
        robots_note="Confirmado 2026-09-15: no existe robots.txt (404 real del sitio, no bloqueo de borde) → sin restricciones declaradas. Falta validar queries.py/links.py contra HTML real (tarea 13) antes de habilitar.",
    ),
    "mercado_unico": SourceConfig(
        id="mercado_unico",
        name="Mercado Único",
        base_url="https://www.mercado-unico.com",
        list_urls_fn=queries.mercado_unico_list_urls,
        enabled=False,
        # Confirmado 2026-09-15 en el dominio corregido (con guión, sin .ar):
        # User-agent: * -> Allow: / (permiso general). Tiene bloqueos
        # puntuales por nombre de bot para crawlers de entrenamiento de IA
        # (GPTBot, CCBot, Google-Extended, Applebot-Extended, Bytespider,
        # Amazonbot, meta-externalagent, ClaudeBot) vía Content-Signal
        # ai-train=no — no aplica a un bot propio con su propio user-agent,
        # que cae bajo la regla general "User-agent: *: Allow: /". Falta la
        # tarea 13 (validar queries.py/links.py) antes de habilitar.
        robots_note="Confirmado 2026-09-15 en mercado-unico.com: Allow: / general (bloquea por nombre a crawlers de entrenamiento de IA específicos, no aplica a un bot propio). Falta validar queries.py/links.py (tarea 13) antes de habilitar.",
    ),
    "mercadolibre": SourceConfig(
        id="mercadolibre",
        name="Mercado Libre Inmuebles",
        base_url="https://inmuebles.mercadolibre.com.ar",
        list_urls_fn=lambda: iter([]),  # TODO: agregar generador de listado en queries.py
        enabled=False,
        # Confirmado 2026-09-15: 403 Forbidden con la página de error propia
        # de MercadoLibre incluso pidiendo /robots.txt — bot protection fuerte
        # como se esperaba. No confirmable con curl simple.
        robots_note="2026-09-15: 403 Forbidden (bot protection propia de ML) incluso para /robots.txt — confirma lo esperado, no invertir tiempo acá por ahora.",
    ),
    "properati": SourceConfig(
        id="properati",
        name="Properati",
        base_url="https://www.properati.com.ar",
        list_urls_fn=lambda: iter([]),  # TODO: agregar generador de listado en queries.py
        enabled=False,
        # Confirmado 2026-09-15: 403 Forbidden (awselb) incluso para
        # /robots.txt — bot protection a nivel de load balancer, antes de
        # llegar a la app. No confirmable con curl simple.
        robots_note="2026-09-15: 403 Forbidden (AWS ELB) incluso para /robots.txt — bot protection en el borde, no confirmable con curl simple. No habilitar por ahora.",
    ),
}
