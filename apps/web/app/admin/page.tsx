'use client';
import {useEffect,useState,useCallback} from 'react';
import {useRouter} from 'next/navigation';
import {
  getPendingAgencies,approveAgency,rejectAgency,getReviewQueue,resolveReviewItem,
  getColdStartPending,markColdStartSent,ColdStartTaskItem,listAdminAgencies,reopenAgency,
  PendingAgency,ReviewQueueItem,adminAuthMe,
} from '../../lib/api';

const ADMIN_TOKEN_KEY = 'propomi-admin-token';
const ADMIN_USER_KEY = 'propomi-admin-user';

type Tab = 'pending'|'review'|'coldstart'|'directory';

/**
 * Panel admin humano. Sesión = JWT en sessionStorage (no localStorage).
 * Sin token válido → /admin/login.
 */
export default function AdminPage(){
  const router = useRouter();
  const [token,setToken]=useState<string|null>(null);
  const [username,setUsername]=useState('');
  const [ready,setReady]=useState(false);
  const [tab,setTab]=useState<Tab>('pending');
  const [pending,setPending]=useState<PendingAgency[]>([]);
  const [review,setReview]=useState<ReviewQueueItem[]>([]);
  const [coldStart,setColdStart]=useState<ColdStartTaskItem[]>([]);
  const [directory,setDirectory]=useState<PendingAgency[]>([]);
  const [dirStatus,setDirStatus]=useState('');
  const [dirQ,setDirQ]=useState('');
  const [notes,setNotes]=useState<Record<string,string>>({});
  const [loading,setLoading]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const [toast,setToast]=useState<string|null>(null);
  const [counts,setCounts]=useState<{pending:number;review:number;coldstart:number}>({pending:0,review:0,coldstart:0});

  useEffect(()=>{
    const t = sessionStorage.getItem(ADMIN_TOKEN_KEY);
    const u = sessionStorage.getItem(ADMIN_USER_KEY)||'';
    if(!t){
      router.replace('/admin/login');
      return;
    }
    adminAuthMe(t).then(()=>{
      setToken(t);
      setUsername(u);
      setReady(true);
    }).catch(()=>{
      sessionStorage.removeItem(ADMIN_TOKEN_KEY);
      sessionStorage.removeItem(ADMIN_USER_KEY);
      router.replace('/admin/login');
    });
  },[router]);

  const logout = useCallback(()=>{
    sessionStorage.removeItem(ADMIN_TOKEN_KEY);
    sessionStorage.removeItem(ADMIN_USER_KEY);
    router.replace('/admin/login');
  },[router]);

  async function loadCounts(t:string){
    try{
      const [p,r,c]=await Promise.all([
        getPendingAgencies(t),
        getReviewQueue(t),
        getColdStartPending(t),
      ]);
      setCounts({pending:p.length,review:r.items?.length??r.count??0,coldstart:c.length});
    }catch{/* ignore */}
  }

  async function loadTab(){
    if(!token)return;
    setLoading(true);setError(null);
    try{
      if(tab==='pending')setPending(await getPendingAgencies(token));
      else if(tab==='review')setReview((await getReviewQueue(token)).items);
      else if(tab==='coldstart')setColdStart(await getColdStartPending(token));
      else {
        const r=await listAdminAgencies(token,{status:dirStatus||undefined,q:dirQ||undefined,limit:200});
        setDirectory(r.items);
      }
    }catch(e:any){
      if(e?.status===401){setError('Sesión admin inválida.');logout()}
      else setError(e?.message||'No se pudo cargar.');
    }finally{setLoading(false)}
  }

  useEffect(()=>{if(token){loadTab();loadCounts(token)}},[token,tab]); // eslint-disable-line react-hooks/exhaustive-deps

  async function reload(){if(token){await Promise.all([loadTab(),loadCounts(token)])}}

  async function doApprove(id:string){
    if(!token)return;
    try{await approveAgency(id,token,notes[id]?.trim()||undefined);setToast('Agencia verificada.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo aprobar.')}
  }
  async function doReject(id:string){
    if(!token)return;
    try{await rejectAgency(id,token,notes[id]?.trim()||undefined);setToast('Agencia rechazada.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo rechazar.')}
  }
  async function doResolve(id:string,action:'confirm_duplicate'|'not_duplicate'){
    if(!token)return;
    try{await resolveReviewItem(id,action,token);setToast(action==='confirm_duplicate'?'Marcado como duplicado.':'Descartado.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo resolver.')}
  }
  async function doReopen(id:string){
    if(!token)return;
    try{await reopenAgency(id,token,notes[id]?.trim()||undefined);setToast('Agencia vuelta a PENDING.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo reabrir.')}
  }
  async function doMarkSent(id:string){
    if(!token)return;
    try{await markColdStartSent(id,token,notes[id]?.trim()||undefined);setToast('Marcado como enviado.');reload()}
    catch(e:any){setToast(e?.message||'No se pudo marcar.')}
  }

  function igHref(ig?:string|null){
    if(!ig)return null;
    const h=ig.replace(/^@/,'').trim();
    if(!h)return null;
    if(h.startsWith('http'))return h;
    return `https://instagram.com/${h}`;
  }

  if(!ready)return <div className="container" style={{padding:48}}><p className="muted">Verificando sesión…</p></div>;

  return <div className="container" style={{padding:'32px 0',maxWidth:960}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:16,gap:12,flexWrap:'wrap'}}>
      <div>
        <h1 style={{fontSize:24,margin:0}}>Admin Propomi</h1>
        <p className="muted small" style={{margin:0}}>Sesión: {username||'admin'} · se borra al cerrar la pestaña</p>
      </div>
      <button className="secondary" onClick={logout}>Cerrar sesión</button>
    </div>

    <div style={{display:'flex',gap:8,marginBottom:20,flexWrap:'wrap'}}>
      {([
        ['pending',`Pendientes (${counts.pending})`],
        ['review',`Duplicados (${counts.review})`],
        ['coldstart',`Cold-start (${counts.coldstart})`],
        ['directory','Directorio'],
      ] as [Tab,string][]).map(([k,label])=>(
        <button key={k} className={tab===k?'primary':'secondary'} onClick={()=>setTab(k)} style={{padding:'8px 12px',fontSize:13}}>{label}</button>
      ))}
    </div>

    {error && <div className="notice" style={{marginBottom:12}}>{error}</div>}
    {loading && <p className="muted small">Cargando…</p>}

    {tab==='pending' && (
      <div>
        <p className="muted small" style={{marginBottom:12}}>Cola de verificación. Prioridad alta primero.</p>
        {pending.length===0 && !loading ? <div className="empty">No hay agencias pendientes.</div> : (
          <div style={{display:'flex',flexDirection:'column',gap:16}}>
            {pending.map(a=>(
              <div key={a.id} className="card" style={{padding:16,border:'1px solid #e2e7ed',borderRadius:12,background:'#fff'}}>
                <div style={{display:'flex',justifyContent:'space-between',gap:12,flexWrap:'wrap'}}>
                  <div>
                    <div style={{fontWeight:700,fontSize:16}}>{a.name}</div>
                    <div className="muted small">{a.city} · id {a.id}</div>
                  </div>
                  <div className="muted small">Prioridad: <b>{a.verificationPriority??0}</b></div>
                </div>
                <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:8,marginTop:12,fontSize:14}}>
                  <div>Tel: <b>{a.phone||'—'}</b></div>
                  <div>Claimed: {a.claimed?'sí':'no'}</div>
                  <div>Instagram: {a.instagram ? (
                    <a href={igHref(a.instagram)||'#'} target="_blank" rel="noreferrer">{a.instagram}</a>
                  ) : '—'}</div>
                  <div>Web: {a.websiteLink ? (
                    <a href={a.websiteLink} target="_blank" rel="noreferrer">{a.websiteLink}</a>
                  ) : '—'}</div>
                </div>
                <label style={{display:'block',marginTop:12,fontSize:13}}>Notas (opcional)
                  <input value={notes[a.id]||''} onChange={e=>setNotes(n=>({...n,[a.id]:e.target.value}))} placeholder="Motivo o comentario de revisión"/>
                </label>
                <div style={{display:'flex',gap:8,marginTop:12}}>
                  <button className="primary" onClick={()=>doApprove(a.id)}>Aprobar</button>
                  <button className="secondary" onClick={()=>doReject(a.id)}>Rechazar</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    )}

    {tab==='review' && (
      <div>
        {review.length===0 && !loading ? <div className="empty">Sin ítems en cola de duplicados.</div> : (
          <div className="tablewrap"><table><thead><tr>
            <th>Título</th><th>Zona</th><th>Posible dup de</th><th></th>
          </tr></thead><tbody>
            {review.map((item:any)=>(
              <tr key={item.id}>
                <td>{item.title||item.id}</td>
                <td>{item.zone||'—'}</td>
                <td>{item.possibleDuplicateOf||'—'}</td>
                <td style={{display:'flex',gap:6}}>
                  <button className="secondary" style={{padding:'4px 8px',fontSize:12}} onClick={()=>doResolve(item.id,'confirm_duplicate')}>Es dup</button>
                  <button className="secondary" style={{padding:'4px 8px',fontSize:12}} onClick={()=>doResolve(item.id,'not_duplicate')}>No es</button>
                </td>
              </tr>
            ))}
          </tbody></table></div>
        )}
      </div>
    )}

    {tab==='coldstart' && (
      <div>
        {coldStart.length===0 && !loading ? <div className="empty">Sin tareas cold-start.</div> : (
          <div className="tablewrap"><table><thead><tr>
            <th>Agencia</th><th>Tel</th><th>Resumen</th><th></th>
          </tr></thead><tbody>
            {coldStart.map((t:any)=>(
              <tr key={t.id}>
                <td>{t.agencyName||t.agency_id||'—'}</td>
                <td>{t.phone||'—'}</td>
                <td className="small">{t.offerSummary||t.summary||'—'}</td>
                <td><button className="secondary" style={{padding:'4px 8px',fontSize:12}} onClick={()=>doMarkSent(t.id)}>Marcar enviado</button></td>
              </tr>
            ))}
          </tbody></table></div>
        )}
      </div>
    )}

    {tab==='directory' && (
      <div>
        <div style={{display:'flex',gap:8,marginBottom:12,flexWrap:'wrap'}}>
          <input placeholder="Buscar" value={dirQ} onChange={e=>setDirQ(e.target.value)} style={{flex:1,minWidth:140}}/>
          <select value={dirStatus} onChange={e=>setDirStatus(e.target.value)}>
            <option value="">Todos</option>
            <option value="PENDING">PENDING</option>
            <option value="VERIFIED">VERIFIED</option>
            <option value="REJECTED">REJECTED</option>
          </select>
          <button className="primary" onClick={loadTab} disabled={loading}>Buscar</button>
        </div>
        {directory.length===0 ? <div className="empty">Sin resultados.</div> : (
          <div className="tablewrap"><table><thead><tr>
            <th>Nombre</th><th>Estado</th><th>Ciudad</th><th>Tel</th><th>IG</th><th></th>
          </tr></thead><tbody>
            {directory.map(a=>(
              <tr key={a.id}>
                <td>{a.name}<div className="muted small">{a.id}</div></td>
                <td>{a.verificationStatus}</td>
                <td>{a.city}</td>
                <td>{a.phone||'—'}</td>
                <td>{a.instagram||'—'}</td>
                <td>
                  {a.verificationStatus!=='PENDING' && (
                    <button className="secondary" style={{padding:'4px 8px',fontSize:12}} onClick={()=>doReopen(a.id)}>Reabrir</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody></table></div>
        )}
      </div>
    )}

    {toast && <div className="toast" onClick={()=>setToast(null)}>{toast}</div>}
  </div>;
}
