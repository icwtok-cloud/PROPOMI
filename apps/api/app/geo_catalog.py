"""Catálogo geográfico estático para el formulario de alta de agencia.

Estructura: país → provincias/departamentos → ciudades/localidades principales.
No depende de Property (a diferencia de GET /properties/filters).
Cobertura razonable de ciudades principales; no exhaustiva de cada pueblo.
"""

from __future__ import annotations

# Argentina: provincia → ciudades principales
_AR: dict[str, list[str]] = {
    "Buenos Aires": [
        "La Plata", "Mar del Plata", "Bahía Blanca", "Tandil", "San Nicolás",
        "Pilar", "Tigre", "San Isidro", "Vicente López", "Avellaneda",
        "Quilmes", "Lomas de Zamora", "Morón", "San Martín", "Lanús",
        "Almirante Brown", "Esteban Echeverría", "Ezeiza", "Merlo", "Moreno",
        "José C. Paz", "Malvinas Argentinas", "San Fernando", "Escobar",
        "Campana", "Zárate", "Necochea", "Olavarría", "Junín", "Pergamino",
    ],
    "CABA": ["Ciudad Autónoma de Buenos Aires"],
    "Catamarca": ["San Fernando del Valle de Catamarca", "Belén", "Andalgalá"],
    "Chaco": ["Resistencia", "Presidencia Roque Sáenz Peña", "Villa Ángela"],
    "Chubut": ["Rawson", "Comodoro Rivadavia", "Puerto Madryn", "Trelew", "Esquel"],
    "Córdoba": [
        "Córdoba", "Villa Carlos Paz", "Río Cuarto", "Villa María",
        "San Francisco", "Alta Gracia", "Jesús María", "La Falda",
    ],
    "Corrientes": ["Corrientes", "Goya", "Paso de los Libres", "Mercedes"],
    "Entre Ríos": ["Paraná", "Concordia", "Gualeguaychú", "Concepción del Uruguay"],
    "Formosa": ["Formosa", "Clorinda"],
    "Jujuy": ["San Salvador de Jujuy", "Palpalá", "San Pedro"],
    "La Pampa": ["Santa Rosa", "General Pico"],
    "La Rioja": ["La Rioja", "Chilecito"],
    "Mendoza": [
        "Mendoza", "Godoy Cruz", "Guaymallén", "Maipú", "Luján de Cuyo",
        "San Rafael", "San Martín",
    ],
    "Misiones": ["Posadas", "Oberá", "Eldorado", "Puerto Iguazú"],
    "Neuquén": ["Neuquén", "Cutral Có", "Plottier", "Zapala", "San Martín de los Andes"],
    "Río Negro": ["Viedma", "Bariloche", "General Roca", "Cipolletti", "Allen"],
    "Salta": ["Salta", "San Ramón de la Nueva Orán", "Tartagal"],
    "San Juan": ["San Juan", "Rawson", "Rivadavia", "Chimbas"],
    "San Luis": ["San Luis", "Villa Mercedes"],
    "Santa Cruz": ["Río Gallegos", "Caleta Olivia", "El Calafate", "Puerto Deseado"],
    "Santa Fe": [
        "Santa Fe", "Rosario", "Rafaela", "Venado Tuerto", "Reconquista",
        "Santo Tomé", "Villa Gobernador Gálvez",
    ],
    "Santiago del Estero": ["Santiago del Estero", "La Banda", "Termas de Río Hondo"],
    "Tierra del Fuego": ["Ushuaia", "Río Grande"],
    "Tucumán": ["San Miguel de Tucumán", "Yerba Buena", "Tafí Viejo", "Concepción"],
}

# Paraguay: departamento → ciudades principales
_PY: dict[str, list[str]] = {
    "Asunción": ["Asunción"],
    "Central": [
        "San Lorenzo", "Luque", "Capiatá", "Lambaré", "Fernando de la Mora",
        "Limpio", "Ñemby", "Mariano Roque Alonso", "Villa Elisa", "San Antonio",
    ],
    "Alto Paraná": ["Ciudad del Este", "Hernandarias", "Presidente Franco", "Mingá Guazú"],
    "Itapúa": ["Encarnación", "Carmen del Paraná", "Hohenau"],
    "Caaguazú": ["Coronel Oviedo", "Caaguazú"],
    "Cordillera": ["Caacupé", "Tobatí"],
    "Guairá": ["Villarrica"],
    "Misiones": ["San Juan Bautista"],
    "Paraguarí": ["Paraguarí"],
    "San Pedro": ["San Pedro de Ycuamandiyú"],
    "Concepción": ["Concepción"],
    "Amambay": ["Pedro Juan Caballero"],
    "Canindeyú": ["Salto del Guairá"],
    "Ñeembucú": ["Pilar"],
    "Presidente Hayes": ["Villa Hayes"],
    "Boquerón": ["Filadelfia"],
    "Alto Paraguay": ["Fuerte Olimpo"],
    "Caazapá": ["Caazapá"],
}

# Uruguay: departamento → ciudades principales
_UY: dict[str, list[str]] = {
    "Montevideo": ["Montevideo"],
    "Canelones": [
        "Canelones", "Ciudad de la Costa", "Las Piedras", "Pando",
        "La Paz", "Toledo", "Progreso", "Atlántida", "Parque del Plata",
    ],
    "Maldonado": ["Maldonado", "Punta del Este", "San Carlos", "Piriápolis"],
    "Colonia": ["Colonia del Sacramento", "Nueva Helvecia", "Carmelo", "Juan Lacaze"],
    "Salto": ["Salto"],
    "Paysandú": ["Paysandú"],
    "Rivera": ["Rivera"],
    "Tacuarembó": ["Tacuarembó"],
    "Cerro Largo": ["Melo"],
    "Rocha": ["Rocha", "La Paloma", "Chuy"],
    "Lavalleja": ["Minas"],
    "Florida": ["Florida"],
    "San José": ["San José de Mayo", "Ciudad del Plata"],
    "Soriano": ["Mercedes"],
    "Río Negro": ["Fray Bentos"],
    "Artigas": ["Artigas"],
    "Durazno": ["Durazno"],
    "Flores": ["Trinidad"],
    "Treinta y Tres": ["Treinta y Tres"],
}

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
