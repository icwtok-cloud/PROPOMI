'use client';
import {useEffect,useState} from 'react';
import {getAnalyticsDemand} from '../lib/api';
import {DemandSummary,Session} from '../lib/types';

/**
 * Etapa 3 v2 (fase Intelligence): panel de demanda agregada para el
 * dashboard de agencia. Lee GET /analytics/demand (backend main.py v5),
 * que agrega los eventos search_performed guardados desde Etapa 3 v1 en
 * GET /properties.
 *
 * Usa estilos inline a propósito: el resto del proyecto (AgentDashboard,
 * etc.) usa clases CSS propias definidas en globals.css que este archivo
 * no tiene visibilidad para reutilizar sin riesgo de romper algo — los
 * estilos inline no dependen de ninguna clase externa y quedan
 * autocontenidos, aunque visualmente sean más simples que el resto.
 */
export default function DemandPanel({session}:{session:Session|null}){
  const [data,setData]=useState<DemandSummary|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);

  useEffect(()=>{
    let cancelled=false;
    setLoading(true);setError(null);
    getAnalyticsDemand(session)
      .then(d=>{if(!cancelled)setData(d)})
      .catch(e=>{if(!cancelled)setError(e?.message||'No pudimos cargar la demanda.')})
      .finally(()=>{if(!cancelled)setLoading(false)});
    return ()=>{cancelled=true};
  },[session]);

  if(loading) return <p className="muted small">Cargando demanda…</p>;
  if(error) return <div className="notice notice-error">{error}</div>;
  if(!data||data.sampleSize===0) return <div className="empty">Todavía no hay suficientes búsquedas registradas para mostrar demanda.</div>;

  return <div style={{display:'flex',flexDirection:'column',gap:16}}>
    <p className="muted small">Basado en las últimas {data.sampleSize} búsquedas de compradores en la plataforma.</p>
    <RankingBlock title="Zonas más buscadas" items={data.topZones.map(z=>({label:z.zone,count:z.count}))}/>
    <RankingBlock title="Tipos más buscados" items={data.topTypes.map(t=>({label:t.type,count:t.count}))}/>
    <RankingBlock title="Operaciones más buscadas" items={data.topOperations.map(o=>({label:o.operation,count:o.count}))}/>
    {data.avgResultCount!==null && (
      <p className="muted small">
        Promedio de {data.avgResultCount.toFixed(1)} propiedades encontradas por búsqueda.
        {data.avgResultCount<3 && ' Muchas búsquedas encuentran poca oferta — puede ser una oportunidad para publicar más en esas zonas.'}
      </p>
    )}
  </div>;
}

function RankingBlock({title,items}:{title:string;items:{label:string;count:number}[]}){
  if(items.length===0) return null;
  const max=Math.max(...items.map(i=>i.count));
  return <div>
    <div style={{fontSize:12,fontWeight:600,color:'#6b6b6b',textTransform:'uppercase',letterSpacing:0.4,marginBottom:8}}>{title}</div>
    <div style={{display:'flex',flexDirection:'column',gap:6}}>
      {items.slice(0,5).map(item=>(
        <div key={item.label} style={{display:'flex',alignItems:'center',gap:8}}>
          <span style={{fontSize:14,width:110,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{item.label}</span>
          <div style={{flex:1,height:8,borderRadius:999,background:'#f0ebe6',overflow:'hidden'}}>
            <div style={{height:'100%',borderRadius:999,background:'#c2632f',width:`${(item.count/max)*100}%`}}/>
          </div>
          <span style={{fontSize:12,color:'#9a9a9a',width:20,textAlign:'right'}}>{item.count}</span>
        </div>
      ))}
    </div>
  </div>;
}
