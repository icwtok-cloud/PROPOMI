'use client';
import {useCallback,useEffect,useState} from 'react';
import {
  createDemandRequest,
  deleteDemandRequest,
  getAnalyticsDemand,
  getMarketOpportunities,
  listDemandRequests,
  MarketOpportunities,
} from '../lib/api';
import {DemandRequest,DemandSummary,Session} from '../lib/types';
import {formatMoney} from '../lib/geo';

/**
 * Pestaña Demanda: (1) demandas genéricas premium de la agencia
 * (2) ranking de búsquedas en sus zonas + demanda global.
 */
export default function DemandPanel({session}:{session:Session|null}){
  const [market,setMarket]=useState<MarketOpportunities|null>(null);
  const [data,setData]=useState<DemandSummary|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState<string|null>(null);

  const [requests,setRequests]=useState<DemandRequest[]>([]);
  const [reqLoading,setReqLoading]=useState(false);
  const [reqError,setReqError]=useState<string|null>(null);
  const [planBlocked,setPlanBlocked]=useState<string|null>(null);
  const [busy,setBusy]=useState(false);
  const [zone,setZone]=useState('');
  const [propertyType,setPropertyType]=useState('Departamento');
  const [roomsMin,setRoomsMin]=useState('2');
  const [priceMax,setPriceMax]=useState('');

  const loadRequests=useCallback(async()=>{
    if(!session)return;
    setReqLoading(true);setReqError(null);setPlanBlocked(null);
    try{
      const rows=await listDemandRequests(session);
      setRequests(Array.isArray(rows)?rows:[]);
    }catch(e:any){
      if(e?.status===403){
        setPlanBlocked(e?.message||'La demanda genérica requiere plan Profesional o superior.');
        setRequests([]);
      }else{
        setReqError(e?.message||'No pudimos cargar tus búsquedas publicadas.');
      }
    }finally{
      setReqLoading(false);
    }
  },[session]);

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

  useEffect(()=>{loadRequests()},[loadRequests]);

  async function handleCreate(e:React.FormEvent){
    e.preventDefault();
    if(!session)return;
    const z=zone.trim();
    if(z.length<2){setReqError('Indicá una zona (mín. 2 caracteres).');return}
    const rooms=roomsMin===''?null:Number(roomsMin);
    const price=priceMax===''?null:Number(priceMax);
    if(price!=null&&!(price>0)){setReqError('El precio máximo debe ser mayor a cero.');return}
    setBusy(true);setReqError(null);setPlanBlocked(null);
    try{
      await createDemandRequest({
        zone:z,
        property_type:propertyType,
        rooms_min:rooms!=null&&!Number.isNaN(rooms)?rooms:null,
        price_max:price,
      },session);
      setZone('');setPriceMax('');
      await loadRequests();
    }catch(err:any){
      if(err?.status===403){
        setPlanBlocked(err?.message||'La demanda genérica requiere plan Profesional o superior.');
      }else{
        setReqError(err?.message||'No pudimos publicar la búsqueda.');
      }
    }finally{
      setBusy(false);
    }
  }

  async function handleDelete(id:string){
    if(!session)return;
    setBusy(true);setReqError(null);
    try{
      await deleteDemandRequest(id,session);
      await loadRequests();
    }catch(err:any){
      setReqError(err?.message||'No pudimos eliminar la búsqueda.');
    }finally{
      setBusy(false);
    }
  }

  const fmt=(n:number|null|undefined,cur?:string|null)=>n==null?'—':formatMoney(n, cur);
  const activeRequests=requests.filter(r=>r.active);

  return <div className="demand-stack">
    {/* ——— Busco propiedad (premium) ——— */}
    <div className="summarycard account-block">
      <div className="account-block-head">
        <div>
          <h3 className="account-block-title">Busco propiedad</h3>
          <p className="muted small" style={{margin:0}}>
            Publicá qué estás buscando para otras agencias. Si hay compatibilidad en el catálogo, te avisamos (B2B, sin compradores).
            Disponible en plan Profesional o superior.
          </p>
        </div>
      </div>

      {planBlocked && (
        <div className="notice notice-warn" style={{marginBottom:12}}>
          {planBlocked}{' '}
          <button type="button" className="secondary" style={{marginLeft:8,padding:'6px 12px',fontSize:13}}
            onClick={()=>{
              // Navega a Mi cuenta sin romper AgentDashboard: evento custom
              window.dispatchEvent(new CustomEvent('propomi:goto-cuenta'));
            }}>
            Ver planes
          </button>
        </div>
      )}

      {!planBlocked && (
        <form className="account-form-grid" onSubmit={handleCreate} style={{marginBottom:14}}>
          <label className="agent-field">Zona
            <input value={zone} onChange={e=>setZone(e.target.value)} placeholder="Ej: Nueva Córdoba" required minLength={2}/>
          </label>
          <label className="agent-field">Tipo
            <select value={propertyType} onChange={e=>setPropertyType(e.target.value)} style={{border:'1.5px solid #dfe5ec',borderRadius:12,padding:'11px 14px'}}>
              <option value="Departamento">Departamento</option>
              <option value="Casa">Casa</option>
              <option value="PH">PH</option>
              <option value="Local">Local</option>
              <option value="Terreno">Terreno</option>
            </select>
          </label>
          <label className="agent-field">Ambientes mínimos
            <input type="number" min={0} max={20} value={roomsMin} onChange={e=>setRoomsMin(e.target.value)} placeholder="2"/>
          </label>
          <label className="agent-field">Precio máximo
            <input type="number" min={1} value={priceMax} onChange={e=>setPriceMax(e.target.value)} placeholder="150000"/>
          </label>
          <div className="account-span-2" style={{display:'flex',gap:10,alignItems:'center'}}>
            <button type="submit" className="primary" disabled={busy||!session}>{busy?'Publicando…':'Publicar búsqueda'}</button>
          </div>
        </form>
      )}

      {reqError && <div className="notice notice-error">{reqError}</div>}
      {reqLoading ? (
        <p className="muted small">Cargando tus búsquedas…</p>
      ) : activeRequests.length===0 && !planBlocked ? (
        <div className="empty">Todavía no publicaste una búsqueda genérica.</div>
      ) : activeRequests.length>0 ? (
        <div className="demand-req-list">
          {activeRequests.map(r=>(
            <div key={r.id} className="opprow" style={{display:'flex',justifyContent:'space-between',alignItems:'center',gap:12,flexWrap:'wrap'}}>
              <div>
                <strong>{r.zone}</strong>
                <span className="muted small"> · {r.propertyType}
                  {r.roomsMin!=null?` · ≥ ${r.roomsMin} amb.`:''}
                  {r.priceMax!=null?` · hasta ${fmt(r.priceMax)}`:''}
                </span>
                {r.createdAt && (
                  <div className="muted small">Desde {new Date(r.createdAt).toLocaleDateString('es-AR')}</div>
                )}
              </div>
              <button type="button" className="secondary" disabled={busy} onClick={()=>handleDelete(r.id)}>Eliminar</button>
            </div>
          ))}
        </div>
      ) : null}
    </div>

    {/* ——— Analytics existentes ——— */}
    {loading ? (
      <p className="muted small">Cargando demanda del mercado…</p>
    ) : error ? (
      <div className="notice">{error}</div>
    ) : (
      <>
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
      </>
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
