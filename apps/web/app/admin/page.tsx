'use client';
import {useEffect,useState} from 'react';
import {getPendingAgencies,approveAgency,rejectAgency,getReviewQueue,resolveReviewItem} from '../../lib/api';
import {PendingAgency,ReviewQueueItem} from '../../lib/types';

// Etapa 013: panel interno de administración. Usa X-Admin-Key (pedida una
// sola vez y guardada en localStorage), NUNCA Clerk/OTP — este panel no es
// de cara al comprador/agente, lo opera el equipo de Propomi. Junta lo que
// hasta ahora solo se probaba con curl/Postman: cola de agencias pendientes
// (etapa 4) y cola de duplicados del crawler (etapas 011/012).
const ADMIN_KEY_STORAGE='propomi-admin-key';

export default function AdminPage(){
  const [adminKey,setAdminKey]=useState<string>('');
  const [keyInput,setKeyInput]=useState('');
  const [tab,setTab]=useState<'agencies'|'duplicates'>('agencies');
  const [agencies,setAgencies]=useState<PendingAgency[]>([]);
  const [queue,setQueue]=useState<ReviewQueueItem[]>([]);
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [toast,setToast]=useState('');

  useEffect(()=>{const saved=localStorage.getItem(ADMIN_KEY_STORAGE);if(saved)setAdminKey(saved)},[]);
  useEffect(()=>{if(toast){const t=setTimeout(()=>setToast(''),3000);return()=>clearTimeout(t)}},[toast]);
  useEffect(()=>{if(adminKey)load()},[adminKey,tab]);

  function saveKey(){if(!keyInput.trim())return;localStorage.setItem(ADMIN_KEY_STORAGE,keyInput.trim());setAdminKey(keyInput.trim())}
  function clearKey(){localStorage.removeItem(ADMIN_KEY_STORAGE);setAdminKey('');setKeyInput('');setAgencies([]);setQueue([])}

  async function load(){
    setLoading(true);setError(null);
    try{
      if(tab==='agencies')setAgencies(await getPendingAgencies(adminKey));
      else setQueue((await getReviewQueue(adminKey)).items);
    }catch(e:any){
      if(e?.status===401){setError('Clave de administración inválida.');clearKey()}
      else setError(e?.message||'No se pudo cargar.');
    }finally{setLoading(false)}
  }

  async function doApprove(id:string){try{await approveAgency(id,adminKey);setToast('Agencia verificada.');load()}catch(e:any){setToast(e?.message||'No se pudo aprobar.')}}
  async function doReject(id:string){try{await rejectAgency(id,adminKey);setToast('Agencia rechazada.');load()}catch(e:any){setToast(e?.message||'No se pudo rechazar.')}}
  async function doResolve(id:string,action:'confirm_duplicate'|'not_duplicate'){try{await resolveReviewItem(id,action,adminKey);setToast(action==='confirm_duplicate'?'Marcada como duplicado y ocultada.':'Marcada como no-duplicado.');load()}catch(e:any){setToast(e?.message||'No se pudo resolver.')}}

  if(!adminKey){
    return <div className="container" style={{padding:'60px 0',maxWidth:420}}>
      <h2>Panel interno</h2>
      <p className="muted">Ingresá la clave de administración (X-Admin-Key) para continuar.</p>
      <div className="formgrid" style={{gridTemplateColumns:'1fr'}}>
        <input type="password" value={keyInput} onChange={e=>setKeyInput(e.target.value)} placeholder="Clave de administración" onKeyDown={e=>e.key==='Enter'&&saveKey()}/>
      </div>
      <div className="modalactions" style={{marginTop:14}}>
        <button className="primary" onClick={saveKey}>Entrar</button>
      </div>
    </div>;
  }

  return <div className="container" style={{padding:'40px 0'}}>
    <div className="opphead">
      <h2>Panel interno</h2>
      <button className="secondary" onClick={clearKey}>Cambiar clave</button>
    </div>
    <div className="filterrow" style={{margin:'18px 0'}}>
      <button className={tab==='agencies'?'tab active':'tab'} style={{color:tab==='agencies'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('agencies')}>Agencias pendientes</button>
      <button className={tab==='duplicates'?'tab active':'tab'} style={{color:tab==='duplicates'?'#102033':undefined,borderColor:'#d9e0e8'}} onClick={()=>setTab('duplicates')}>Posibles duplicados</button>
    </div>

    {error && <div className="notice notice-error">{error}</div>}
    {loading && <p className="muted">Cargando…</p>}

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

    {toast && <div className="toast">{toast}</div>}
  </div>;
}
