/** Catálogos geográficos canónicos (UI). Independientes del inventario actual. */

export const AR_PROVINCES: string[] = [
  'Buenos Aires',
  'CABA',
  'Catamarca',
  'Chaco',
  'Chubut',
  'Córdoba',
  'Corrientes',
  'Entre Ríos',
  'Formosa',
  'Jujuy',
  'La Pampa',
  'La Rioja',
  'Mendoza',
  'Misiones',
  'Neuquén',
  'Río Negro',
  'Salta',
  'San Juan',
  'San Luis',
  'Santa Cruz',
  'Santa Fe',
  'Santiago del Estero',
  'Tierra del Fuego',
  'Tucumán',
];

/** 17 departamentos de Paraguay */
export const PY_DEPARTMENTS: string[] = [
  'Alto Paraguay',
  'Alto Paraná',
  'Amambay',
  'Asunción',
  'Boquerón',
  'Caaguazú',
  'Caazapá',
  'Canindeyú',
  'Central',
  'Concepción',
  'Cordillera',
  'Guairá',
  'Itapúa',
  'Misiones',
  'Ñeembucú',
  'Paraguarí',
  'Presidente Hayes',
  'San Pedro',
];

/** 19 departamentos de Uruguay */
export const UY_DEPARTMENTS: string[] = [
  'Artigas',
  'Canelones',
  'Cerro Largo',
  'Colonia',
  'Durazno',
  'Flores',
  'Florida',
  'Lavalleja',
  'Maldonado',
  'Montevideo',
  'Paysandú',
  'Río Negro',
  'Rivera',
  'Rocha',
  'Salto',
  'San José',
  'Soriano',
  'Tacuarembó',
  'Treinta y Tres',
];

/** 32 entidades federativas de México (nombres cortos de uso habitual) */
export const MX_STATES: string[] = [
  'Aguascalientes',
  'Baja California',
  'Baja California Sur',
  'Campeche',
  'Chiapas',
  'Chihuahua',
  'Ciudad de México',
  'Coahuila',
  'Colima',
  'Durango',
  'Estado de México',
  'Guanajuato',
  'Guerrero',
  'Hidalgo',
  'Jalisco',
  'Michoacán',
  'Morelos',
  'Nayarit',
  'Nuevo León',
  'Oaxaca',
  'Puebla',
  'Querétaro',
  'Quintana Roo',
  'San Luis Potosí',
  'Sinaloa',
  'Sonora',
  'Tabasco',
  'Tamaulipas',
  'Tlaxcala',
  'Veracruz',
  'Yucatán',
  'Zacatecas',
];

export function canonicalAdminUnits(country: string): string[] {
  if (country === 'Argentina') return AR_PROVINCES;
  if (country === 'Paraguay') return PY_DEPARTMENTS;
  if (country === 'Uruguay') return UY_DEPARTMENTS;
  if (country === 'México' || country === 'Mexico') return MX_STATES;
  return [];
}

/** Label del 2º nivel territorial según país del buscador. */
export function adminUnitLabel(country: string): string {
  if (country === 'Paraguay' || country === 'Uruguay') return 'Departamento';
  if (country === 'México' || country === 'Mexico') return 'Estado';
  if (country === 'Argentina') return 'Provincia';
  return 'Provincia / Departamento';
}

/** Label visible del tipo vivienda “Departamento” según país (valor interno no cambia). */
export function propertyTypeLabel(typeName: string, country: string): string {
  if (typeName === 'Departamento' && country === 'Uruguay') return 'Apartamento';
  return typeName;
}
