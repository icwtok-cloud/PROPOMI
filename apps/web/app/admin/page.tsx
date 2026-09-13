use client';
import {useEffect,useState} from 'react';
import {
  getPendingAgencies,approveAgency,rejectAgency,getReviewQueue,resolveReviewItem,
  getColdStartPending,markColdStartSent,ColdStartTaskItem,
} from '../../lib/api';
import {PendingAgency,ReviewQueueItem} from '../../lib/types';

const ADMIN_KEY_STORAGE='propomi-admin-key';

export default function AdminPage(){
  const [adminKey,setAdminKey]=useState<string>('');
  const [keyInput,setKeyInput]=useState('');
  const [tab,setTab]=useState<'agencies'|'duplicates'|'coldstart'>('agencies');
  const [agencies,setAgencies]=useState<PendingAgency[]>([]);
  const [queue,setQueue]=useState<ReviewQueueItem[]>([]);
  const [coldStart,setColdStart]=useState<ColdStartTaskItem[]>([]);
  const [counts,setCounts]=useState({agencies:0,duplicates:0,coldstart:0});
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [toast,setToast]=useState('');
  const [notes,setNotes]=useState<Record<string,string>>({});

  useEffect(()=>{const saved=localStorage.getItem(ADMIN_KEY_STORAGE);if(saved)setAdminKey(saved)},[]);
  useEffect(()=>{if(toast){const t=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(t)}},[toast]);
  useEffect(()=>{if(adminKey){loadTab();loadCounts()}},[adminKey,tab]);

  function saveKey(){if(!keyInput.trim())return;localStorage.setItem(ADMIN_KEY_STORAGE,keyInput.trim());setAdminKey(keyInput.trim())}
  function clearKey(){
    localStorage.removeItem(ADMIN_KEY_STORAGE);
    setAdminKey('');setKeyInput('');setAgencies([]);setQueue([]);setColdStart([]);
    setCounts({agencies:0,duplicates:0,coldstart:0});
  }
  function setNote(id:string,v:string){setNotes(n=>({...n,[id]:v}))}

  async function loadCounts(){
    try{
      const [a,d,c]=await Promise.all([
        getPendingAgencies(adminKey),
        getReviewQueue(adminKey),
        getColdStartPending(adminKey),
      ]);
      setCounts({agencies:a.length,duplicates:d.items?.length||0,coldstart:c.length});
    }catch{/* counts best-effort */}
  }

  async function loadTab(){
    setLoading(true);setError(null);
    try{
      if(tab==='agencies')setAgencies(await getPendingAgencies(adminKey));
      else if(tab==='duplicates')setQueue((await getReviewQueue(adminKey)).items);
      else setColdStart(await getColdStartPending(adminKey));
    }catch(e:any){
      if(e?.status===401){setError('Clave de administración inválida.');clearKey()}
      else setError(e?.message||'No se pudo cargar.');
    }finally{setLoading(false)}
  }

  async function reload(){await Promise.all([loadTab(),loadCounts()])}

  async function doApprove(id:string){
    try{await approveAgency(id,adminKey,notes[id]?.trim()||undefined);setToast('Agencia verificada.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo aprobar.')}
  }
  async function doReject(id:string){
    try{await rejectAgency(id,adminKey,notes[id]?.trim()||undefined);setToast('Agencia rechazada.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo rechazar.')}
  }
  async function doResolve(id:string,action:'confirm_duplicate'|'not_duplicate'){
    try{await resolveReviewItem(id,action,adminKey);setToast(action==='confirm_duplicate'?'Marcado como duplicado.':'Descartado.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo resolver.')}
  }
  async function doMarkSent(id:string){
    try{await markColdStartSent(id,adminKey,notes[id]?.trim()||undefined);setToast('Marcado como enviado.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo marcar.')}
  }
  async function copyText(text:string){
    try{await navigator.clipboard.writeText(text);setToast('Copiado al portapapeles.')}
    catch{setToast('No se pudo copiar — seleccioná el texto a mano.')}
  }

  if(!adminKey){
    return <div className="container" style={{padding:'48px 0',maxWidth:420}}>
      <h1 style={{fontSize:24,marginBottom:8}}>Admin Propomi</h1>
      <p className="muted">Ingresá la clave de administración (X-Admin-Key) para continuar.</p>
      <label>Clave<input type="password" value={keyInput} onChange={e=>setKeyInput(e.target.value)} onKeyDown={e=>{if(e.key==='Enter')saveKey()}}/></label>
      <button className="primary" style={{marginTop:12}} onClick={saveKey}>Entrar</button>
      {error && <div className="notice" style={{marginTop:12}}>{error}</div>}
    </div>;
  }

  return <div className="container" style={{padding:'36px 0 64px'}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16,gap:12,flexWrap:'wrap'}}>
      <h1 style={{fontSize:24,margin:0}}>Admin Propomi</h1>
      <div style={{display:'flex',gap:8}}>
        <button className="secondary" onClick={reload} disabled={loading}>Recargar</button>
        <button className="secondary" onClick={clearKey}>Cerrar sesión</button>
      </div>
    </div>

    <div className="agentmetrics" style={{marginBottom:20}}>
      <div><b>{counts.agencies}</b><span>Agencias pendientes</span></div>
      <div><b>{counts.duplicates}</b><span>Duplicados a revisar</span></div>
      <div><b>{counts.coldstart}</b><span>Cold start pendientes</span></div>
    </div>

    <div style={{display:'flex',gap:8,marginBottom:20,flexWrap:'wrap'}}>
      <button className={tab==='agencies'?'tab active':'tab'} style={{color:tab==='agencies'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('agencies')}>
        Agencias {counts.agencies>0?`(${counts.agencies})`:''}
      </button>
      <button className={tab==='duplicates'?'tab active':'tab'} style={{color:tab==='duplicates'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('duplicates')}>
        Duplicados {counts.duplicates>0?`(${counts.duplicates})`:''}
      </button>
      <button className={tab==='coldstart'?'tab active':'tab'} style={{color:tab==='coldstart'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('coldstart')}>
        Cold start {counts.coldstart>0?`(${counts.coldstart})`:''}
      </button>
    </div>

    {error && <div className="notice" style={{marginBottom:16}}>{error}</div>}
    {loading && <div className="muted">Cargando…</div>}

    {!loading && tab==='agencies' && (
      agencies.length===0 ? <div className="empty">No hay agencias pendientes de revisión.</div> :
      <div style={{display:'flex',flexDirection:'column',gap:16}}>
        {agencies.map(a=>(
          <div key={a.id} className="summarycard" style={{padding:16}}>
            <div style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
              <div>
                <div><b>{a.name}</b> · {a.city}</div>
                <div className="muted small">Tel: {a.phone||'—'} · IG: {a.instagram||'—'}{a.websiteLink?` · ${a.websiteLink}`:''}</div>
                <div className="muted small">{a.verificationPriority>0?'Prioritaria':'Normal'} · claimed: {a.claimed?'sí':'no'}</div>
              </div>
              <div style={{display:'flex',gap:6,alignItems:'flex-start'}}>
                <button className="primary" onClick={()=>doApprove(a.id)}>Aprobar</button>
                <button className="secondary" onClick={()=>doReject(a.id)}>Rechazar</button>
              </div>
            </div>
            <label style={{marginTop:10,display:'block'}}>
              Notas (opcional)
              <input value={notes[a.id]||''} onChange={e=>setNote(a.id,e.target.value)} placeholder="Motivo de aprobación/rechazo"/>
            </label>
          </div>
        ))}
      </div>
    )}

    {!loading && tab==='duplicates' && (
      queue.length===0 ? <div className="empty">No hay posibles duplicados esperando revisión.</div> :
      <div style={{display:'flex',flexDirection:'column',gap:16}}>
        {queue.map(item=>
          <div key={item.property.id} className="summarycard" style={{padding:16}}>
            <div className="formgrid">
              <div>
                <div className="qlabel">Nueva</div>
                <div><b>{item.property.title}</b></div>
                <div className="muted small">{item.property.zone} · USD {item.property.price.toLocaleString('en-US')} · {item.property.surface} m² · {item.property.source}</div>
              </div>
              <div>
                <div className="qlabel">Posible duplicado de</div>
                {item.candidate ? <>
                  <div><b>{item.candidate.title}</b></div>
                  <div className="muted small">{item.candidate.zone} · USD {item.candidate.price.toLocaleString('en-US')} · {item.candidate.surface} m² · {item.candidate.source}</div>
                </> : <div className="muted small">(la propiedad candidata ya no existe)</div>}
              </div>
            </div>
            <div className="modalactions" style={{marginTop:14}}>
              <button className="secondary" onClick={()=>doResolve(item.property.id,'not_duplicate')}>No es duplicado</button>
              <button className="primary" onClick={()=>doResolve(item.property.id,'confirm_duplicate')}>Confirmar duplicado</button>
            </div>
          </div>
        )}
      </div>
    )}

    {!loading && tab==='coldstart' && (
      coldStart.length===0 ? <div className="empty">No hay notificaciones cold-start pendientes.</div> :
      <div style={{display:'flex',flexDirection:'column',gap:16}}>
        <p className="muted small">Envío manual: copiá el mensaje, mandalo por WhatsApp/SMS, después marcá como enviado. El teléfono solo se muestra acá (admin).</p>
        {coldStart.map(t=>
          <div key={t.id} className="summarycard" style={{padding:16}}>
            <div style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
              <div>
                <div><b>{t.propertyTitle}</b></div>
                <div className="muted small">{t.propertyZone} · {t.currency} {Number(t.amount).toLocaleString('en-US')}</div>
                <div className="muted small">Tel: {t.targetPhone}</div>
                <div className="muted small">Onboarding: {t.onboardingPath}</div>
                {t.createdAt && <div className="muted small">Creado: {new Date(t.createdAt).toLocaleString('es-AR')}</div>}
              </div>
              <div style={{display:'flex',gap:6,alignItems:'flex-start',flexWrap:'wrap'}}>
                <button className="secondary" onClick={()=>copyText(t.messageTemplate)}>Copiar mensaje</button>
                <button className="secondary" onClick={()=>copyText(t.targetPhone)}>Copiar tel</button>
                <button className="primary" onClick={()=>doMarkSent(t.id)}>Marcar enviado</button>
              </div>
            </div>
            <label style={{marginTop:10,display:'block'}}>
              Notas al marcar enviado (opcional)
              <input value={notes[t.id]||''} onChange={e=>setNote(t.id,e.target.value)} placeholder="Ej. enviado por WA 11:30"/>
            </label>
            <pre style={{marginTop:12,whiteSpace:'pre-wrap',fontSize:12,background:'#f5f7fa',padding:12,borderRadius:8}}>{t.messageTemplate}</pre>
          </div>
        )}
      </div>
    )}

    {toast && <div className="toast">{toast}</div>}
  </div>;
}
