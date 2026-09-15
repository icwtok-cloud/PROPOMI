'use client';
import {useEffect,useState} from 'react';
import {getAnalyticsDemand,getMarketOpportunities,MarketOpportunities} from '../lib/api';
import {DemandSummary,Session} from '../lib/types';

/**
 * T5.7: oportunidades de mercado — cruce de search_performed con zonas
 * del catálogo de la agencia. Estilos migrados a classes de globals.css
 * (demand-*) manteniendo el look previo.
 */
export default function DemandPanel({session}:{session:Session|null}){
  const [market,setMarket]=useState<MarketOpportunities|null>(null);
  const [data,setData]=useState<DemandSummary|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);

  useEffect(()=>{
    let cancelled=false;
    setLoading(true);setError(null);
    const agencyId=session?.user?.agency_id;
    Promise.all([
      agencyId&&session?getMarketOpportunities(agencyId,session,30):Promise.resolve(null),
      getAnalyticsDemand(session),
    ])
      .then(([m,d])=>{
        if(cancelled)return;
        setMarket(m);
        setData(d);
      })
      .catch(e=>{if(!cancelled)setError(e?.message||'No pudimos cargar la demanda.')})
      .finally(()=>{if(!cancelled)setLoading(false)});
    return ()=>{cancelled=true};
  },[session]);

  if(loading) return <p className="muted small">Cargando demanda…</p>;
  if(error) return <div className="notice">{error}</div>;

  const fmt=(n:number|null|undefined)=>n==null?'—':`USD ${Number(n).toLocaleString('en-US')}`;

  return <div className="demand-stack">
    <div>
      <div className="demand-label">Oportunidades en tus zonas</div>
      <p className="muted small demand-lead">
        Búsquedas de compradores (últimos {market?.days??30} días) solo en zonas donde tenés publicaciones. Datos agregados y anónimos.
      </p>
      {!market||market.zones.length===0 ? (
        <div className="empty">Publicá propiedades para ver demanda en tus zonas.</div>
      ) : (
        <div className="tablewrap">
          <table>
            <thead>
              <tr>
                <th>Zona</th>
                <th>Tus props</th>
                <th>Búsquedas</th>
                <th>Presupuesto (rango)</th>
                <th>Tipo top</th>
                <th>Amb. top</th>
              </tr>
            </thead>
            <tbody>
              {market.zones.map(z=>(
                <tr key={z.zone}>
                  <td>{z.zone}</td>
                  <td>{z.agencyListingCount}</td>
                  <td>{z.searchCount}</td>
                  <td>{z.searchCount===0?'—':`${fmt(z.budgetMin)} – ${fmt(z.budgetMax)}`}</td>
                  <td>{z.topType||'—'}</td>
                  <td>{z.topRooms||'—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {market&&market.sampleSize>0 && (
        <p className="muted small demand-sample">Muestra: {market.sampleSize} búsquedas con zona que matchea tu catálogo.</p>
      )}
    </div>

    {data&&data.sampleSize>0 && (
      <div>
        <div className="demand-label">Demanda global (contexto)</div>
        <p className="muted small">Últimas {data.sampleSize} búsquedas en toda la plataforma.</p>
        <RankingBlock title="Zonas más buscadas" items={data.topZones.map(z=>({label:z.zone,count:z.count}))}/>
        <RankingBlock title="Tipos más buscados" items={data.topTypes.map(t=>({label:t.type,count:t.count}))}/>
      </div>
    )}
  </div>;
}

function RankingBlock({title,items}:{title:string;items:{label:string;count:number}[]}){
  if(items.length===0) return null;
  const max=Math.max(...items.map(i=>i.count));
  return <div className="demand-rank">
    <div className="demand-rank-title">{title}</div>
    <div className="demand-rank-list">
      {items.slice(0,5).map(item=>(
        <div key={item.label} className="demand-rank-row">
          <span className="demand-rank-label">{item.label}</span>
          <div className="demand-bar-track">
            <div className="demand-bar-fill" style={{width:`${(item.count/max)*100}%`}}/>
          </div>
          <span className="demand-rank-count">{item.count}</span>
        </div>
      ))}
    </div>
  </div>;
}
