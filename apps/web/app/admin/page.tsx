use client';
import {useEffect,useState} from 'react';
import {
  getPendingAgencies,approveAgency,rejectAgency,getReviewQueue,resolveReviewItem,
  getColdStartPending,markColdStartSent,ColdStartTaskItem,
} from '../../lib/api';
import {PendingAgency,ReviewQueueItem} from '../../lib/types';

// Panel interno: agencias pendientes, duplicados crawler, y cola cold-start
// (T6.1). X-Admin-Key en localStorage — nunca OTP/Clerk.
const ADMIN_KEY_STORAGE='propomi-admin-key';

export default function AdminPage(){
  const [adminKey,setAdminKey]=useState<string>('');
  const [keyInput,setKeyInput]=useState('');
  const [tab,setTab]=useState<'agencies'|'duplicates'|'coldstart'>('agencies');
  const [agencies,setAgencies]=useState<PendingAgency[]>([]);
  const [queue,setQueue]=useState<ReviewQueueItem[]>([]);
  const [coldStart,setColdStart]=useState<ColdStartTaskItem[]>([]);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [toast,setToast]=useState('');

  useEffect(()=>{const saved=localStorage.getItem(ADMIN_KEY_STORAGE);if(saved)setAdminKey(saved)},[]);
  useEffect(()=>{if(toast){const t=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(t)}},[toast]);
  useEffect(()=>{if(adminKey)load()},[adminKey,tab]);

  function saveKey(){if(!keyInput.trim())return;localStorage.setItem(ADMIN_KEY_STORAGE,keyInput.trim());setAdminKey(keyInput.trim())}
  function clearKey(){
    localStorage.removeItem(ADMIN_KEY_STORAGE);
    setAdminKey('');setKeyInput('');setAgencies([]);setQueue([]);setColdStart([]);
  }

  async function load(){
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

  async function doApprove(id:string){try{await approveAgency(id,adminKey);setToast('Agencia verificada.');load()}catch(e:any){setToast(e?.message||'No se pudo aprobar.')}}
  async function doReject(id:string){try{await rejectAgency(id,adminKey);setToast('Agencia rechazada.');load()}catch(e:any){setToast(e?.message||'No se pudo rechazar.')}}
  async function doResolve(id:string,action:'confirm_duplicate'|'not_duplicate'){
    try{await resolveReviewItem(id,action,adminKey);setToast(action==='confirm_duplicate'?'Marcado como duplicado.':'Descartado.');load()}
    catch(e:any){setToast(e?.message||'No se pudo resolver.')}
  }
  async function doMarkSent(id:string){
    try{await markColdStartSent(id,adminKey);setToast('Marcado como enviado.');load()}
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
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:20}}>
      <h1 style={{fontSize:24,margin:0}}>Admin Propomi</h1>
      <button className="secondary" onClick={clearKey}>Cerrar sesión</button>
    </div>

    <div style={{display:'flex',gap:8,marginBottom:20,flexWrap:'wrap'}}>
      <button className={tab==='agencies'?'tab active':'tab'} style={{color:tab==='agencies'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('agencies')}>Agencias pendientes</button>
      <button className={tab==='duplicates'?'tab active':'tab'} style={{color:tab==='duplicates'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('duplicates')}>Posibles duplicados</button>
      <button className={tab==='coldstart'?'tab active':'tab'} style={{color:tab==='coldstart'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('coldstart')}>Cold start</button>
    </div>

    {error && <div className="notice" style={{marginBottom:16}}>{error}</div>}
    {loading && <div className="muted">Cargando…</div>}

    {!loading && tab==='agencies' && (
      agencies.length===0 ? <div className="empty">No hay agencias pendientes de revisión.</div> :
      <div className="tablewrap"><table><thead><tr>
        <th>Agencia</th><th>Ciudad</th><th>Teléfono</th><th>Instagram / Web</th><th>Prioridad</th><th></th>
      </tr></thead><tbody>
        {agencies.map(a=><tr key={a.id}>
          <td>{a.name}</td><td>{a.city}</td><td>{a.phone||'—'}</td>
          <td>{a.instagram||'—'}{a.websiteLink?` · ${a.websiteLink}`:''}</td>
          <td>{a.verificationPriority>0?'Prioritaria':'Normal'}</td>
          <td style={{display:'flex',gap:6}}>
            <button className="secondary" onClick={()=>doApprove(a.id)}>Aprobar</button>
            <button className="secondary" onClick={()=>doReject(a.id)}>Rechazar</button>
          </td>
        </tr>)}
      </tbody></table></div>
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
        <p className="muted small">Envío manual: copiá el mensaje, mandalo por WhatsApp/SMS al teléfono, después marcá como enviado. El teléfono solo se muestra acá (admin).</p>
        {coldStart.map(t=>
          <div key={t.id} className="summarycard" style={{padding:16}}>
            <div style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
              <div>
                <div><b>{t.propertyTitle}</b></div>
                <div className="muted small">{t.propertyZone} · {t.currency} {Number(t.amount).toLocaleString('en-US')}</div>
                <div className="muted small">Tel: {t.targetPhone}</div>
                <div className="muted small">Onboarding: {t.onboardingPath}</div>
              </div>
              <div style={{display:'flex',gap:6,alignItems:'flex-start',flexWrap:'wrap'}}>
                <button className="secondary" onClick={()=>copyText(t.messageTemplate)}>Copiar mensaje</button>
                <button className="secondary" onClick={()=>copyText(t.targetPhone)}>Copiar tel</button>
                <button className="primary" onClick={()=>doMarkSent(t.id)}>Marcar enviado</button>
              </div>
            </div>
            <pre style={{marginTop:12,whiteSpace:'pre-wrap',fontSize:12,background:'#f5f7fa',padding:12,borderRadius:8}}>{t.messageTemplate}</pre>
          </div>
        )}
      </div>
    )}

    {toast && <div className="toast">{toast}</div>}
  </div>;
}
