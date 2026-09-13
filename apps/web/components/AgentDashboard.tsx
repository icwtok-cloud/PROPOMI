'use client';
import {useEffect,useState} from 'react';
import {Building2,Check,Copy,ExternalLink,Inbox,Instagram,LogOut,Plus,RefreshCw,ShieldCheck,ShieldQuestion,ShieldX,Sparkles,TrendingUp,User} from 'lucide-react';
import {Agency,Offer,Property,Session} from '../lib/types';
import {getAgentSession,setAgentSession,clearAgentSession,requestOtp,verifyOtp,listOffers,isOffersRestricted,getAgency,updateAgency,relinkAgency,getAgencyOpportunities,getAnalytics,createProperty,getProperties,buildShareUrl} from '../lib/api';
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
  const [offersRestrictedCount,setOffersRestrictedCount]=useState<number|null>(null);
  const [opps,setOpps]=useState<OppData|null>(null);
  const [analytics,setAnalytics]=useState<{properties:number;events:number;offers:number}|null>(null);
  const [section,setSection]=useState<'ofertas'|'oportunidades'|'demanda'|'propiedades'|'cuenta'>('ofertas');
  const [propForm,setPropForm]=useState({title:'',zone:'',city:'Buenos Aires',price:'',surface:'',rooms:'2',description:'',imageUrl:''});
  const [myProperties,setMyProperties]=useState<Property[]>([]);
  const [toast,setToast]=useState('');
  const [nameDraft,setNameDraft]=useState('');
  const [instagramDraft,setInstagramDraft]=useState('');
  const [websiteDraft,setWebsiteDraft]=useState('');
  const [busy,setBusy]=useState(false);

  useEffect(()=>{const s=getAgentSession();setSession(s);setReady(true)},[]);
  useEffect(()=>{if(!session)return;(async()=>{
    const [a,o,opp,an,props]=await Promise.all([
      getAgency(session.user.agency_id,session),
      listOffers(session),
      getAgencyOpportunities(session.user.agency_id,session),
      getAnalytics(session),
      getProperties({agency_id:session.user.agency_id}),
    ]);
    setAgency(a);setNameDraft(a.name);setInstagramDraft(a.instagram||'');setWebsiteDraft(a.websiteLink||'');
    if(isOffersRestricted(o)){setOffers([]);setOffersRestrictedCount(o.count)}
    else{setOffers(o);setOffersRestrictedCount(null)}
    setOpps(opp as OppData);setAnalytics(an as any);setMyProperties(props);
  })().catch(()=>{})},[session]);

  function notify(msg:string){setToast(msg);setTimeout(()=>setToast(''),3500)}

  async function copyShareLink(propertyId:string){
    const origin=agency?.slug||'agente';
    const url=buildShareUrl(propertyId,origin);
    try{
      await navigator.clipboard.writeText(url);
      notify('Link copiado (origen: '+origin+').');
    }catch{
      notify('No se pudo copiar. URL: '+url);
    }
  }

  async function refreshOffers(){
    if(!session)return;
    const o=await listOffers(session);
    if(isOffersRestricted(o)){setOffers([]);setOffersRestrictedCount(o.count)}
    else{setOffers(o);setOffersRestrictedCount(null)}
  }

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

  async function submitProperty(){
    if(!session)return;
    if(agency?.verificationStatus!=='VERIFIED'){
      notify('Solo agencias verificadas pueden cargar propiedades.');
      return;
    }
    const title=propForm.title.trim();
    const zone=propForm.zone.trim();
    const city=propForm.city.trim()||'Buenos Aires';
    const price=Number(propForm.price);
    const surface=Number(propForm.surface);
    const rooms=Number(propForm.rooms)||2;
    if(!title||!zone||!(price>0)||!(surface>0)){
      notify('Completá título, zona, precio y superficie.');
      return;
    }
    setBusy(true);
    try{
      const images=propForm.imageUrl.trim()?[propForm.imageUrl.trim()]:[];
      await createProperty({
        title,zone,city,price,surface,rooms,
        type:'Departamento',operation:'Venta',currency:'USD',
        description:propForm.description.trim()||undefined,
        images,
      },session);
      setPropForm({title:'',zone:'',city:'Buenos Aires',price:'',surface:'',rooms:'2',description:'',imageUrl:''});
      notify('Propiedad publicada.');
      try{
        const [an,props]=await Promise.all([
          getAnalytics(session),
          getProperties({agency_id:session.user.agency_id}),
        ]);
        setAnalytics(an as any);
        setMyProperties(props);
      }catch{}
    }catch(e:any){
      notify(e?.message||'No pudimos publicar la propiedad.');
    }finally{
      setBusy(false);
    }
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
      <div><b>{offersRestrictedCount!==null?offersRestrictedCount:offers.filter(o=>o.status==='SENT').length}</b><span>Ofertas nuevas</span></div>
      <div><b>{opps?.active??0}</b><span>Oportunidades activas</span></div>
      <div><b>{offers.filter(o=>o.contact_revealed).length}</b><span>Contactos revelados</span></div>
      <div><b>{analytics?.properties??0}</b><span>Publicaciones</span></div>
      <div><b>{agency?.freeLeadsRemaining??0}</b><span>Reveals gratis restantes</span></div>
    </div>

    <div className="agentdashtabs">
      <button className={section==='ofertas'?'tab active':'tab'} onClick={()=>setSection('ofertas')}><Inbox size={15}/> Ofertas</button>
      <button className={section==='oportunidades'?'tab active':'tab'} onClick={()=>setSection('oportunidades')}><Sparkles size={15}/> Oportunidades</button>
      <button className={section==='demanda'?'tab active':'tab'} onClick={()=>setSection('demanda')}><TrendingUp size={15}/> Demanda</button>
      <button className={`tab${section==='propiedades'?' active':''}`} onClick={()=>setSection('propiedades')}><Plus size={14}/> Propiedades</button>
      <button className={section==='cuenta'?'tab active':'tab'} onClick={()=>setSection('cuenta')}><User size={15}/> Mi cuenta</button>
    </div>

    {section==='ofertas' && <div className="agentdashpane">
      {agency?.verificationStatus!=='VERIFIED' && (
        <div className="notice">
          {offersRestrictedCount && offersRestrictedCount>0
            ? <>Tenés <strong>{offersRestrictedCount}</strong> oferta{offersRestrictedCount===1?'':'s'} esperando — verificá tu cuenta para verlas y poder revelar contactos.</>
            : <>Tu agencia está <strong>{agency?.verificationStatus==='REJECTED'?'rechazada':'pendiente de verificación'}</strong>. Cuando esté Verificada vas a poder ver el detalle de las ofertas y revelar contactos.</>}
          {' '}Completá Instagram en Mi cuenta si todavía no lo hiciste.
        </div>
      )}
      {agency?.verificationStatus==='VERIFIED' && offers.length===0 && (
        <div className="empty">Todavía no recibiste ofertas. En cuanto un comprador proponga un precio en alguna de tus publicaciones, va a aparecer acá.</div>
      )}
      {agency?.verificationStatus==='VERIFIED' && offers.map(o=><div key={o.id} className="offercard">
        <div className="offercardhead"><strong>USD {o.amount.toLocaleString('en-US')}</strong><span className="pill">{o.status}</span></div>
        {o.origin && <p className="muted small">Origen: {o.origin}</p>}
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

    {section==='propiedades' && <div className="agentdashpane">
      {agency?.verificationStatus!=='VERIFIED' && (
        <div className="notice">
          Tu agencia tiene que estar <strong>Verificada</strong> para publicar propiedades. Completá Instagram en Mi cuenta y esperá la revisión.
        </div>
      )}

      <div className="summarycard">
        <strong>Tus publicaciones</strong>
        <span className="muted small">{myProperties.length} propiedad{myProperties.length===1?'':'es'}</span>
      </div>
      {myProperties.length===0 && <div className="empty">Todavía no tenés propiedades publicadas en Propomi.</div>}
      {myProperties.map(p=>(
        <div key={p.id} className="opprow" style={{alignItems:'flex-start',flexDirection:'column',gap:4}}>
          <div style={{display:'flex',justifyContent:'space-between',width:'100%',gap:12,alignItems:'flex-start'}}>
            <div>
              <strong>{p.title}</strong>
              <div className="muted small">{p.zone} · {p.surface} m² · {p.rooms} amb.{p.needsReview?' · en revisión':''}</div>
            </div>
            <div style={{display:'flex',flexDirection:'column',alignItems:'flex-end',gap:6}}>
              <span>{p.currency} {Number(p.price).toLocaleString('en-US')}</span>
              <button type="button" className="secondary" style={{padding:'6px 10px',fontSize:12}} onClick={()=>copyShareLink(p.id)}>
                <Copy size={13}/> Copiar link
              </button>
            </div>
          </div>
        </div>
      ))}

      <hr style={{border:'none',borderTop:'1px solid #e3e8ee',margin:'8px 0'}}/>
      <strong>Publicar nueva</strong>
      <label>Título<input value={propForm.title} onChange={e=>setPropForm(f=>({...f,title:e.target.value}))} placeholder="2 ambientes luminoso en Palermo"/></label>
      <label>Zona<input value={propForm.zone} onChange={e=>setPropForm(f=>({...f,zone:e.target.value}))} placeholder="Palermo"/></label>
      <label>Ciudad<input value={propForm.city} onChange={e=>setPropForm(f=>({...f,city:e.target.value}))} placeholder="Buenos Aires"/></label>
      <label>Precio (USD)<input type="number" min={1} value={propForm.price} onChange={e=>setPropForm(f=>({...f,price:e.target.value}))} placeholder="120000"/></label>
      <label>Superficie (m²)<input type="number" min={1} value={propForm.surface} onChange={e=>setPropForm(f=>({...f,surface:e.target.value}))} placeholder="48"/></label>
      <label>Ambientes<input type="number" min={0} value={propForm.rooms} onChange={e=>setPropForm(f=>({...f,rooms:e.target.value}))}/></label>
      <label>URL de foto (opcional)<input value={propForm.imageUrl} onChange={e=>setPropForm(f=>({...f,imageUrl:e.target.value}))} placeholder="https://..."/></label>
      <label>Descripción (sin teléfonos ni links)<textarea value={propForm.description} onChange={e=>setPropForm(f=>({...f,description:e.target.value}))} rows={3} placeholder="Ambientes luminosos, buena ubicación..."/></label>
      <div className="modalactions" style={{justifyContent:'flex-start'}}>
        <button className="primary" disabled={busy||agency?.verificationStatus!=='VERIFIED'} onClick={submitProperty}><Plus size={15}/> Publicar propiedad</button>
      </div>
      <p className="muted small">La descripción no puede incluir teléfonos, emails ni links — Propomi protege el contacto de ambas partes.</p>
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

      <div className="summarycard" style={{marginTop:8}}>
        <strong>Tu plan (solo lectura)</strong>
        <p className="muted small" style={{margin:'6px 0'}}>
          {agency?.subscriptionTier
            ? <>Plan: <b>{agency.subscriptionTier}</b>
                {agency.planLeadQuota==null
                  ? ' · cupo ilimitado este período'
                  : ` · ${agency.leadsUsedCurrentPeriod??0} / ${agency.planLeadQuota} reveals del plan`}
              </>
            : <>Sin suscripción activa — los reveals van por créditos gratis o pago por lead.</>}
        </p>
        <p className="muted small" style={{margin:0}}>
          Créditos gratis restantes: <b>{agency?.freeLeadsRemaining??0}</b>
          {agency?.subscriptionStartedAt ? ` · desde ${new Date(agency.subscriptionStartedAt).toLocaleDateString('es-AR')}` : ''}
        </p>
        <p className="muted small">La contratación/cambio de plan se habilita cuando Lemon y T5.1 estén confirmados.</p>
      </div>

      <p className="muted small">Tu teléfono de acceso es el mismo que usan tus publicaciones para identificarte automáticamente como dueño.</p>
    </div>}

    {toast && <div className="toast"><Check size={17}/>{toast}</div>}
  </div>;
}