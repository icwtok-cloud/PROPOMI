'use client';
import { Property } from '../lib/types';
import { X } from 'lucide-react';

type Row = { key: string; get: (p: Property) => string | number };

const ROWS: Row[] = [
  { key: 'Precio', get: (p) => `USD ${Number(p.price||0).toLocaleString('en-US')}` },
  { key: 'Superficie', get: (p) => p.surface != null ? `${p.surface} m²` : 'N/D' },
  { key: 'Ambientes', get: (p) => p.rooms ?? 'N/D' },
  { key: 'Dormitorios', get: (p) => p.bedrooms ?? 'N/D' },
  { key: 'Baños', get: (p) => p.bathrooms ?? 'N/D' },
  { key: 'Zona', get: (p) => p.zone || 'N/D' },
  { key: 'Ciudad', get: (p) => p.city || 'N/D' },
  { key: 'Tipo', get: (p) => p.type || 'N/D' },
  { key: 'Cochera', get: (p) => (p.parking ? 'Sí' : 'No') },
  { key: 'Balcón', get: (p) => (p.balcony ? 'Sí' : 'No') },
  { key: 'Pileta', get: (p) => (p.pool ? 'Sí' : 'No') },
  { key: 'Crédito', get: (p) => (p.credit ? 'Sí' : 'No') },
  { key: 'Mascotas', get: (p) => (p.petFriendly ? 'Sí' : 'No') },
];

export default function ComparePanel({ items, onClose }: { items: Property[]; onClose: () => void }) {
  if (items.length < 2) {
    return (
      <div className="modalback">
        <div className="modal">
          <div className="modalhead">
            <div>
              <span className="eyebrow">Capa de decisión</span>
              <h2>Comparador</h2>
            </div>
            <button className="close" onClick={onClose} type="button"><X /></button>
          </div>
          <p className="muted">Elegí al menos <strong>2 propiedades</strong> con el botón «Comparar» en las fichas. Después volvé a abrir el comparador.</p>
          <p className="muted small">Ahora tenés {items.length} seleccionada{items.length === 1 ? '' : 's'}.</p>
          <button className="primary" type="button" onClick={onClose} style={{marginTop: 12}}>Seguir eligiendo</button>
        </div>
      </div>
    );
  }

  return (
    <div className="modalback">
      <div className="modal wide">
        <div className="modalhead">
          <div>
            <span className="eyebrow">Capa de decisión</span>
            <h2>Comparador</h2>
            <p className="muted">No buscamos solamente el precio más bajo. Buscamos qué opción tiene más sentido.</p>
          </div>
          <button className="close" onClick={onClose} type="button"><X /></button>
        </div>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Variable</th>
                {items.map((p) => (
                  <th key={p.id}>
                    <div className="muted small" style={{fontWeight: 500, maxWidth: 160, whiteSpace: 'normal'}}>
                      {(p.title || '').slice(0, 48)}{(p.title || '').length > 48 ? '…' : ''}
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.key}>
                  <td><b>{row.key}</b></td>
                  {items.map((p) => <td key={p.id}>{row.get(p)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
