"""Configuración por fuente: dominio, generador de URLs de listado, robots_note.

Estado 2026-09-19b:
  enabled=True (19): 14 portales + 5 agencias TIER A; previas + argencasas, departamentosenpozo, bullano,
    mercadolibre_mx, grupoedisur. ML AR/MX con paginación _Desde_N.
  enabled=False: zonaprop/argenprop/properati + cola SPA/anti-bot.
run_crawl() salta fuentes con enabled=False.
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
        enabled=True,
        # Confirmado 2026-09-15: /robots.txt devuelve 404 (la propia página de
        # error 404 de Next.js del sitio, no un bloqueo de borde) — es decir,
        # el sitio no publica un robots.txt. Por el estándar (RFC 9309),
        # ausencia de robots.txt = no hay restricciones declaradas. Queda
        # limpio del lado de robots.txt; falta la tarea 13 (validar
        # queries.py/links.py contra HTML real) antes de habilitar.
        robots_note="2026-09-15: robots 404 (sin restricción). Sitemap + __NEXT_DATA__ validados; enabled=True.",
    ),
    "mercado_unico": SourceConfig(
        id="mercado_unico",
        name="Mercado Único",
        base_url="https://www.mercado-unico.com",
        list_urls_fn=queries.mercado_unico_list_urls,
        enabled=True,
        robots_note="2026-09-15: Allow:/ (CF managed). Homepage expone /propiedades/{ObjectId}; ficha NUXT+og. enabled=True.",
    ),
    "mercadolibre": SourceConfig(
        id="mercadolibre",
        name="Mercado Libre Inmuebles",
        base_url="https://inmuebles.mercadolibre.com.ar",
        list_urls_fn=queries.mercadolibre_list_urls,
        enabled=True,
        robots_note="2026-09-15 re-eval: list+detail 200 sin challenge; JSON-LD Product viable. list_urls=mercadolibre_list_urls. enabled=True.",
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
    "inmoup": SourceConfig(
        id="inmoup",
        name="InmoUp",
        base_url="https://inmoup.com.ar",
        list_urls_fn=queries.inmoup_list_urls,
        enabled=True,
        robots_note="Confirmado 2026-09-15: Allow general (bloquea /panel/ /json/ maps de ficha). HTML real 200 sin challenge; JSON-LD schema.org RealEstateListing. Foco Mendoza/Cuyo (~25k avisos). list_urls=inmoup_list_urls.",
    ),
    "inmoclick": SourceConfig(
        id="inmoclick",
        name="InmoClick",
        base_url="https://www.inmoclick.com.ar",
        list_urls_fn=queries.inmoclick_list_urls,
        enabled=True,
        robots_note="2026-09-15: robots Allow; listados provinciales 200 sin challenge; fichas /inmuebles/{id}/ficha/. enabled=True.",
    ),

    

    "infocasas_py": SourceConfig(
        id="infocasas_py",
        name="InfoCasas Paraguay",
        base_url="https://www.infocasas.com.py",
        list_urls_fn=queries.infocasas_py_list_urls,
        enabled=True,
        robots_note="2026-09-16: robots 200 Allow; list/detail SSR __NEXT_DATA__; fichas /{slug}/{id}. País completo PY.",
    ),
    "infocasas_uy": SourceConfig(
        id="infocasas_uy",
        name="InfoCasas Uruguay",
        base_url="https://www.infocasas.com.uy",
        list_urls_fn=queries.infocasas_uy_list_urls,
        enabled=True,
        robots_note="2026-09-16: robots 200 Allow; mismo backend que PY; list/detail __NEXT_DATA__. País completo UY.",
    ),
    "bienesonline": SourceConfig(
        id="bienesonline",
        name="BienesOnline Argentina",
        base_url="https://bienesonline.ai",
        list_urls_fn=queries.bienesonline_list_urls,
        enabled=True,
        robots_note="2026-09-16: bienesonline.com.ar → bienesonline.ai; robots 200; listado con href /propiedad/{id}; ficha JSON-LD RealEstateListing. Cobertura AR multi-provincia.",
    ),
    # --- Expansión 2026-09-19: fuera de portales clásicos + ML MX ---
    "argencasas": SourceConfig(
        id="argencasas",
        name="Argencasas",
        base_url="https://www.argencasas.com",
        list_urls_fn=queries.argencasas_list_urls,
        enabled=True,
        robots_note="2026-09-19: listado /venta + /propiedad-* fichas; JSON-LD RealEstateListing; sin CF.",
    ),
    "departamentosenpozo": SourceConfig(
        id="departamentosenpozo",
        name="DepartamentosEnPozo",
        base_url="https://departamentosenpozo.com.ar",
        list_urls_fn=queries.departamentosenpozo_list_urls,
        enabled=True,
        robots_note="2026-09-19: catálogo /desarrollos-inmobiliarios/ (~800 proyectos); HTML limpio; tipo En Pozo.",
    ),
    "bullano": SourceConfig(
        id="bullano",
        name="Bullano Campos",
        base_url="https://www.bullano.com.ar",
        list_urls_fn=queries.bullano_list_urls,
        enabled=True,
        robots_note="2026-09-19: /campos/ficha/{slug}-{id}.html; campos y chacras; sin CF.",
    ),
    "mercadolibre_mx": SourceConfig(
        id="mercadolibre_mx",
        name="MercadoLibre MX",
        base_url="https://inmuebles.mercadolibre.com.mx",
        list_urls_fn=queries.mercadolibre_mx_list_urls,
        enabled=True,
        robots_note="2026-09-19: mismo patrón ML AR (poly-card + JSON-LD Product); prefijo MLM-; estados prioritarios.",
    ),
    "grupoedisur": SourceConfig(
        id="grupoedisur",
        name="Grupo Edisur",
        base_url="https://www.grupoedisur.com.ar",
        list_urls_fn=queries.grupoedisur_list_urls,
        enabled=True,
        robots_note="2026-09-19: /desarrollos/* fichas estáticas; pozo Córdoba; sin CF.",
    ),
    # --- Cola anti-bot / no viable (2026-09-16 triage) — enabled=False ---
    "remax_ar": SourceConfig(
        id="remax_ar",
        name="RE/MAX Argentina",
        base_url="https://www.remax.com.ar",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: robots 200 pero listados /listings/buy y /propiedades son shell sin hrefs de ficha ni JSON-LD/__NEXT_DATA__ (SPA). Sin discovery estático.",
    ),
    "remax_py": SourceConfig(
        id="remax_py",
        name="RE/MAX Paraguay",
        base_url="https://www.remax.com.py",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: robots 200 Allow; homepage/listado ~2.5KB sin fichas (vacío o bloqueo soft). No extractable.",
    ),
    "remax_uy": SourceConfig(
        id="remax_uy",
        name="RE/MAX Uruguay",
        base_url="https://www.remax.com.uy",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: robots 200 (mismo patrón AR); pendiente validar listado — asumir SPA como AR hasta re-eval.",
    ),
    "gallito_uy": SourceConfig(
        id="gallito_uy",
        name="Gallito Uruguay",
        base_url="https://www.gallito.com.uy",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: robots 200 Allow+sitemap; listado /inmuebles → 403 Cloudflare challenge.",
    ),
    "nestoria_ar": SourceConfig(
        id="nestoria_ar",
        name="Nestoria Argentina",
        base_url="https://www.nestoria.com.ar",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: robots.txt 401 Access Denied (bloqueo de borde).",
    ),
    "infocasas_ar": SourceConfig(
        id="infocasas_ar",
        name="InfoCasas Argentina",
        base_url="https://www.infocasas.com.ar",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: DNS no resuelve www.infocasas.com.ar desde el entorno de triage (ERR). Re-evaluar; mismo producto que PY/UY si vuelve.",
    ),
    "century21_ar": SourceConfig(
        id="century21_ar",
        name="Century21 Argentina",
        base_url="https://www.century21.com.ar",
        list_urls_fn=lambda: iter([]),
        enabled=False,
        robots_note="2026-09-16: robots 200; /propiedades 404; home 200 sin patrón de ficha claro en triage — pendiente URL de listado real.",
    ),


    # --- Agencias TIER A verified (2026-09-19 smoke) ---
    "agency_paganini_ar": SourceConfig(
        id="agency_paganini_ar",
        name="Paganini (Rosario)",
        base_url="https://paganini.com.ar",
        list_urls_fn=queries.agency_paganini_ar_list_urls,
        enabled=True,
        robots_note="2026-09-19: Tokko CMS; /propiedades?operation[]=1 venta; fichas /propiedad/{slug}--{id}; sin CF.",
    ),
    "agency_prey_ar": SourceConfig(
        id="agency_prey_ar",
        name="Prey (Rosario)",
        base_url="https://preypropiedades.com",
        list_urls_fn=queries.agency_prey_ar_list_urls,
        enabled=True,
        robots_note="2026-09-19: Tokko CMS (mismo template que Paganini); /propiedad/{slug}--{id}; sin CF.",
    ),
    "agency_prop_uy": SourceConfig(
        id="agency_prop_uy",
        name="PROP (Montevideo)",
        base_url="https://prop.com.uy",
        list_urls_fn=queries.agency_prop_uy_list_urls,
        enabled=True,
        robots_note="2026-09-19: /propiedades/comprar; fichas ...-pNNNNNN; sin CF.",
    ),
    "agency_orangehome_mx": SourceConfig(
        id="agency_orangehome_mx",
        name="Orange Home (Guadalajara)",
        base_url="https://www.orangehomeinmobiliaria.com.mx",
        list_urls_fn=queries.agency_orangehome_mx_list_urls,
        enabled=True,
        robots_note="2026-09-19: home + /{id}/inmuebles/{slug}; moneda MXN; sin CF.",
    ),
    "agency_nuevaalianza_py": SourceConfig(
        id="agency_nuevaalianza_py",
        name="Nueva Alianza (Asunción)",
        base_url="https://inmobiliariana.com.py",
        list_urls_fn=queries.agency_nuevaalianza_py_list_urls,
        enabled=True,
        robots_note="2026-09-19: /propiedad/{id}; listado venta; sin CF.",
    ),


    # --- Agencias TIER B (2026-09-19 discovery) ---
    "agency_brokers_py": SourceConfig(
        id="agency_brokers_py",
        name="Brokers (Paraguay)",
        base_url="https://www.brokers.com.py",
        list_urls_fn=queries.agency_brokers_py_list_urls,
        enabled=True,
        robots_note="2026-09-19 TIER B: home ~248 fichas /propiedad/{id}_slug; sin CF.",
    ),
    "agency_canepa_uy": SourceConfig(
        id="agency_canepa_uy",
        name="Cánepa & Cánepa (UY)",
        base_url="https://www.canepa.com.uy",
        list_urls_fn=queries.agency_canepa_uy_list_urls,
        enabled=True,
        robots_note="2026-09-19 TIER B: /casas|apartamentos|terrenos/en-venta/ + /{Tipo}/{id}; sin CF.",
    ),

}
