'use client';
import {useEffect,useState} from 'react';
import {Building2,Check,ExternalLink,Inbox,Instagram,LogOut,RefreshCw,ShieldCheck,ShieldQuestion,ShieldX,Sparkles,TrendingUp,User} from 'lucide-react';
import {Agency,Offer,Session} from '../lib/types';
import {getAgentSession,setAgentSession,clearAgentSession,requestOtp,verifyOtp,listOffers,getAgency,updateAgency,relinkAgency,getAgencyOpportunities,getAnalytics} from '../lib/api';
import AgentOfferActions from './AgentOfferActions';
import DemandPanel from './DemandPanel';

type OppData={active:number;opportunities:{id:number;property_id?:string;event:string;created_at:string}[];eventCount:number;propertyIds:string[]};

const EVENT_LABELS:Record<string,string>={
  property_view:'Vio una propiedad',property_save:'Guardó una propiedad',property_compare:'Comparó propiedades',
  property_question:'Hizo una consulta',visit_request:'Pidió una visita',offer_created:'Envió una oferta',
  contact_requested:'Solicitó contacto',contact_shared:'Contacto compartido',counter_offer_created:'Contraoferta',
  negotiation_started:'Inició negociación',operation_advanced:'Avanzó la operación',
};

// Espejo de Agency.verificationStatus ('PENDING'|'VERIFIED'|'REJECTED') —
// mismo texto/color en el header y en "Mi cuenta" para no tener dos
// representaciones distintas del mismo estado en la misma pantalla.
function VerificationBadge({status}:{status?:string}){
  if(status==='VERIFIED') return <span className="pill pill-ok"><ShieldCheck size={13}/> Verificada</span>;
  if(status==='REJECTED') return <span className="pill pill-error"><ShieldX size={13}/> Rechazada</span>;
  return <span className="pill pill-pending"><ShieldQuestion size={13}/> Pendiente de verificación</span>;
}

function LoginForm({onLoggedIn}:{onLoggedIn:(s:Session)=>void}){
  const [phone,setPhone]=useState('');
  const [code,setCode]=useState('');
  const [stage,setStage]=useState<'phone'|'code'>('phone');
  const [devCode,setDevCode]=useState<string|undefined>();
  const [error,setError]=useState<string|null>(null);
  const [busy,setBusy]=useState(false);

  async function sendCode(){
    setError(null);
    if(phone.trim().length<6){setError('Ingresá un teléfono válido.');return}
    setBusy(true);
    try{const r=await requestOtp(phone.trim());setDevCode(r.dev_code);setStage('code')}
    catch(e:any){setError(e?.message||'No pudimos enviar el código.')}
    finally{setBusy(false)}
  }
  async function confirmCode(){
    setError(null);
    if(code.trim().length<4){setError('Ingresá el código recibido.');return}
    setBusy(true);
    try{
      const r=await verifyOtp(phone.trim(),code.trim());
      const session={token:r.token,user:r.user};
      setAgentSession(session);
      onLoggedIn(session);
    }catch(e:any){setError(e?.message||'Código incorrecto o vencido.')}
    finally{setBusy(false)}
  }

  return <div className="agentlogin">
    <div className="eyebrow">Acceso de agencia</div>
    <h3>Ingresá con tu celular</h3>
    <p className="muted small">Usamos tu teléfono para vincular automáticamente las publicaciones que ya te pertenecen.</p>
    {stage==='phone' ? (
      <div className="agentloginrow">
        <input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="Ej: 11 5555 0101" inputMode="tel"/>
        <button className="primary" disabled={busy} onClick={sendCode}>{busy?'Enviando…':'Enviar código'}</button>
      </div>
    ) : (
      <div className="agentloginrow">
        <input value={code} onChange={e=>setCode(e.target.value)} placeholder="Código de 6 dígitos" inputMode="numeric"/>
        <button className="primary" disabled={busy} onClick={confirmCode}>{busy?'Verificando…':'Ingresar'}</button>
      </div>
    )}
    {devCode && stage==='code' && <p className="muted small">Modo desarrollo: tu código es <strong>{devCode}</strong></p>}
    {error && <div className="notice notice-error">{error}</div>}
  </div>;
}

export default function AgentDashboard(){
  const [session,setSession]=useState<Session|null>(null);
  const [ready,setReady]=useState(false);
  const [agency,setAgency]=useState<Agency|null>(null);
  const [offers,setOffers]=useState<Offer[]>([]);
  const [opps,setOpps]=useState<OppData|null>(null);
  const [analytics,setAnalytics]=useState<{properties:number;events:number;offers:number}|null>(null);
  const [section,setSection]=useState<'ofertas'|'oportunidades'|'demanda'|'cuenta'>('ofertas');
  const [toast,setToast]=useState('');
  const [nameDraft,setNameDraft]=useState('');
  const [instagramDraft,setInstagramDraft]=useState('');
  const [websiteDraft,setWebsiteDraft]=useState('');
  const [busy,setBusy]=useState(false);

  useEffect(()=>{const s=getAgentSession();setSession(s);setReady(true)},[]);
  useEffect(()=>{if(!session)return;(async()=>{
    const [a,o,opp,an]=await Promise.all([
      getAgency(session.user.agency_id,session),
      listOffers(session),
      getAgencyOpportunities(session.user.agency_id,session),
      getAnalytics(session),
    ]);
    setAgency(a);setNameDraft(a.name);setInstagramDraft(a.instagram||'');setWebsiteDraft(a.websiteLink||'');
    setOffers(o);setOpps(opp as OppData);setAnalytics(an as any);
  })().catch(()=>{})},[session]);

  function notify(msg:string){setToast(msg);setTimeout(()=>setToast(''),3500)}

  async function refreshOffers(){if(!session)return;setOffers(await listOffers(session))}

  // Fix: antes se llamaba updateAgency(id, nameDraft.trim(), session) —
  // pasaba un string donde la función espera {name, instagram, website_link}.
  // Ahora manda los tres campos, coherente con la firma real de api.ts y con
  // lo que el backend necesita para poder pasar de PENDING a VERIFIED (doc 06.2.8).
  async function saveAccount(){
    if(!session||!agency)return;
    setBusy(true);
    try{
      const updated=await updateAgency(session.user.agency_id,{
        name:nameDraft.trim(),
        instagram:instagramDraft.trim()||undefined,
        website_link:websiteDraft.trim()||undefined,
      },session);
      setAgency(prev=>prev?{...prev,...updated}:updated);
      notify('Datos de la agencia actualizados.');
    }catch(e:any){
      notify(e?.message||'No pudimos guardar los cambios.');
    }finally{
      setBusy(false);
    }
  }

  async function relink(){
    if(!session)return;
    setBusy(true);
    try{const r=await relinkAgency(session.user.agency_id,session);notify(r.message)}
    finally{setBusy(false)}
  }

  function logout(){clearAgentSession();setSession(null);setAgency(null);setOffers([]);setOpps(null)}

  if(!ready) return null;

  if(!session) return <div className="container"><div className="agentdash-card"><LoginForm onLoggedIn={setSession}/></div></div>;

  const storefrontPath=agency?.slug?`/tienda/${agency.slug}`:null;

  return <div className="container">
    <div className="agentdashhead">
      <div>
        <span className="eyebrow">Panel de agencia</span>
        <h2>{agency?.name||'Tu agencia'}</h2>
        <p className="muted small">
          {agency?.city}
          {' · '}<VerificationBadge status={agency?.verificationStatus}/>
        </p>
      </div>
      <button className="secondary" onClick={logout}><LogOut size={15}/> Salir</button>
    </div>

    <div className="agentmetrics">
      <div><b>{offers.filter(o=>o.status==='SENT').length}</b><span>Ofertas nuevas</span></div>
      <div><b>{opps?.active??0}</b><span>Oportunidades activas</span></div>
      <div><b>{offers.filter(o=>o.contact_revealed).length}</b><span>Contactos revelados</span></div>
      <div><b>{analytics?.properties??0}</b><span>Publicaciones</span></div>
      <div><b>{agency?.freeLeadsRemaining??0}</b><span>Reveals gratis restantes</span></div>
    </div>

    <div className="agentdashtabs">
      <button className={section==='ofertas'?'tab active':'tab'} onClick={()=>setSection('ofertas')}><Inbox size={15}/> Ofertas</button>
      <button className={section==='oportunidades'?'tab active':'tab'} onClick={()=>setSection('oportunidades')}><Sparkles size={15}/> Oportunidades</button>
      <button className={section==='demanda'?'tab active':'tab'} onClick={()=>setSection('demanda')}><TrendingUp size={15}/> Demanda</button>
      <button className={section==='cuenta'?'tab active':'tab'} onClick={()=>setSection('cuenta')}><User size={15}/> Mi cuenta</button>
    </div>

    {section==='ofertas' && <div className="agentdashpane">
      {offers.length===0 && <div className="empty">Todavía no recibiste ofertas. En cuanto un comprador proponga un precio en alguna de tus publicaciones, va a aparecer acá.</div>}
      {offers.map(o=><div key={o.id} className="offercard">
        <div className="offercardhead"><strong>USD {o.amount.toLocaleString('en-US')}</strong><span className="pill">{o.status}</span></div>
        <div className="muted small">{o.payment_form} · {o.timeframe||'Plazo sin especificar'} · Capital: {o.capital?`USD ${o.capital.toLocaleString('en-US')}`:'—'}</div>
        {o.comment && <p className="muted small">{o.comment}</p>}
        <AgentOfferActions offer={o} session={session} onDone={(m)=>{notify(m);refreshOffers()}}/>
      </div>)}
    </div>}

    {section==='oportunidades' && <div className="agentdashpane">
      {(!opps || opps.opportunities.length===0) && <div className="empty">Sin actividad reciente todavía en tus publicaciones.</div>}
      {opps?.opportunities.map(e=><div key={e.id} className="opprow">
        <span>{EVENT_LABELS[e.event]||e.event}</span>
        <span className="muted small">{new Date(e.created_at).toLocaleString('es-AR')}</span>
      </div>)}
    </div>}

    {section==='demanda' && <div className="agentdashpane">
      <DemandPanel session={session}/>
    </div>}

    {section==='cuenta' && <div className="agentdashpane">
      <label>Nombre de la agencia<input value={nameDraft} onChange={e=>setNameDraft(e.target.value)}/></label>
      <label>Instagram (requerido para verificarte)<input value={instagramDraft} onChange={e=>setInstagramDraft(e.target.value)} placeholder="@tuagencia"/></label>
      <label>Sitio web (opcional)<input value={websiteDraft} onChange={e=>setWebsiteDraft(e.target.value)} placeholder="https://tuagencia.com"/></label>

      {agency?.verificationStatus!=='VERIFIED' && (
        <div className="notice">
          Completá Instagram (y opcionalmente tu sitio) y guardá los cambios: eso es lo que revisa el equipo de Propomi para pasarte a <strong>Verificada</strong> y poder revelar contactos.
        </div>
      )}

      <div className="modalactions" style={{justifyContent:'flex-start'}}>
        <button className="primary" disabled={busy} onClick={saveAccount}><Check size={15}/> Guardar</button>
        <button className="secondary" disabled={busy} onClick={relink}><Building2 size={15}/> Vincular publicaciones por teléfono</button>
      </div>

      {agency?.instagram && (
        <p className="muted small"><Instagram size={13}/> {agency.instagram}</p>
      )}

      {storefrontPath && (
        <p className="muted small">
          Tu vidriera pública: <a href={storefrontPath} target="_blank" rel="noopener noreferrer">{storefrontPath} <ExternalLink size={12}/></a>
        </p>
      )}

      <p className="muted small">Tu teléfono de acceso es el mismo que usan tus publicaciones para identificarte automáticamente como dueño.</p>
    </div>}

    {toast && <div className="toast"><Check size={17}/>{toast}</div>}
  </div>;
}
