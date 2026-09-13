'use client';

import { useEffect, useState } from 'react';
import { getAnalyticsDemand } from '../lib/api';
import type { DemandSummary, Session } from '../lib/types';

/**
 * Etapa 3 v2 (fase Intelligence): panel de demanda agregada para el
 * dashboard de agencia. Lee GET /analytics/demand (backend main.py v5),
 * que a su vez agrega los eventos search_performed guardados desde
 * Etapa 3 v1 en GET /properties.
 *
 * Componente autocontenido: hace su propio fetch con el `session` que le
 * pasa el dashboard (mismo patrón que ya usa el resto de AgentDashboard
 * para llamar a getAnalytics / getAgencyOpportunities). No requiere props
 * adicionales — se integra agregando <DemandPanel session={session} />
 * en cualquier punto del dashboard.
 */
export default function DemandPanel({ session }: { session: Session | null }) {
  const [data, setData] = useState<DemandSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getAnalyticsDemand(session)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.message || 'No pudimos cargar la demanda.');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [session]);

  if (loading) {
    return (
      <div className="rounded-2xl border border-neutral-200 p-4 text-sm text-neutral-500">
        Cargando demanda...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-neutral-200 p-4 text-sm text-red-600">
        {error}
      </div>
    );
  }

  if (!data || data.sampleSize === 0) {
    return (
      <div className="rounded-2xl border border-neutral-200 p-4 text-sm text-neutral-500">
        Todavía no hay suficientes búsquedas registradas para mostrar demanda.
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-neutral-200 p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-neutral-900">Demanda reciente</h3>
        <span className="text-xs text-neutral-400">
          últimas {data.sampleSize} búsquedas
        </span>
      </div>

      <DemandRankingBlock title="Zonas más buscadas" items={data.topZones.map((z) => ({ label: z.zone, count: z.count }))} />
      <DemandRankingBlock title="Tipos más buscados" items={data.topTypes.map((t) => ({ label: t.type, count: t.count }))} />
      <DemandRankingBlock title="Operaciones más buscadas" items={data.topOperations.map((o) => ({ label: o.operation, count: o.count }))} />

      {data.avgResultCount !== null && (
        <p className="text-xs text-neutral-500 pt-2 border-t border-neutral-100">
          Promedio de {data.avgResultCount.toFixed(1)} propiedades devueltas por búsqueda.
          {data.avgResultCount < 3 && ' Muchas búsquedas están encontrando poca oferta — puede ser una oportunidad para publicar más en esas zonas.'}
        </p>
      )}
    </div>
  );
}

function DemandRankingBlock({ title, items }: { title: string; items: { label: string; count: number }[] }) {
  if (items.length === 0) return null;
  const max = Math.max(...items.map((i) => i.count));
  return (
    <div>
      <p className="text-xs font-medium text-neutral-500 uppercase tracking-wide mb-2">{title}</p>
      <ul className="space-y-1.5">
        {items.slice(0, 5).map((item) => (
          <li key={item.label} className="flex items-center gap-2">
            <span className="text-sm text-neutral-700 w-28 truncate">{item.label}</span>
            <div className="flex-1 h-2 rounded-full bg-neutral-100 overflow-hidden">
              <div
                className="h-full rounded-full"
                style={{ width: `${(item.count / max) * 100}%`, backgroundColor: '#c2632f' }}
              />
            </div>
            <span className="text-xs text-neutral-400 w-6 text-right">{item.count}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
