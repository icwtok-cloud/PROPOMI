'use client';
import { Property } from '../lib/types';
import { X } from 'lucide-react';

type Row = { key: string; get: (p: Property) => string | number };

const ROWS: Row[] = [
  { key: 'Precio', get: (p) => `USD ${p.price.toLocaleString('en-US')}` },
  { key: 'Superficie', get: (p) => `${p.surface} m²` },
  { key: 'Ambientes', get: (p) => p.rooms },
  { key: 'Zona', get: (p) => p.zone },
  { key: 'Cochera', get: (p) => (p.parking ? 'Sí' : 'No') },
  { key: 'Crédito', get: (p) => (p.credit ? 'Sí' : 'No') },
  { key: 'Actualización', get: (p) => p.freshness },
];

export default function ComparePanel({ items, onClose }: { items: Property[]; onClose: () => void }) {
  return (
    <div className="modalback">
      <div className="modal wide">
        <div className="modalhead">
          <div>
            <span className="eyebrow">Capa de decisión</span>
            <h2>Comparador</h2>
            <p className="muted">No buscamos solamente el precio más bajo. Buscamos qué opción tiene más sentido.</p>
          </div>
          <button className="close" onClick={onClose}><X /></button>
        </div>
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Variable</th>
                {items.map((p) => <th key={p.id}>{p.title}</th>)}
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
