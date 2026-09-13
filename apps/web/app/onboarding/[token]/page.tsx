"use client";
import {useEffect,useState} from "react";
import {useParams} from "next/navigation";
import {Building2,Check,LogIn} from "lucide-react";
import {
  getOnboarding,
  completeOnboarding,
  requestOtp,
  verifyOtp,
  setAgentSession,
  getAgentSession,
  OnboardingInfo,
} from "../../../lib/api";
import {Session} from "../../../lib/types";

export default function OnboardingPage(){
  const params=useParams();
  const token=String(params?.token||"");
  const [info,setInfo]=useState<OnboardingInfo|null>(null);
  const [error,setError]=useState<string|null>(null);
  const [session,setSession]=useState<Session|null>(null);
  const [phone,setPhone]=useState("");
  const [code,setCode]=useState("");
  const [stage,setStage]=useState<"phone"|"code"|"form">("phone");
  const [devCode,setDevCode]=useState<string|undefined>();
  const [instagram,setInstagram]=useState("");
  const [website,setWebsite]=useState("");
  const [name,setName]=useState("");
  const [busy,setBusy]=useState(false);
  const [done,setDone]=useState<string|null>(null);

  useEffect(()=>{
    const s=getAgentSession();
    if(s){setSession(s);setStage("form")}
  },[]);

  useEffect(()=>{
    if(!token)return;
    (async()=>{
      try{
        const r=await getOnboarding(token);
        setInfo(r);
        if(r.agencyName)setName(r.agencyName);
        if(r.status==="CLAIMED")setDone(r.message||"Perfil ya reclamado.");
      }catch(e:any){
        setError(e?.message||"Link inválido o vencido.");
      }
    })();
  },[token]);

  async function sendCode(){
    setError(null);
    if(phone.trim().length<6){setError("Ingresá un teléfono válido.");return}
    setBusy(true);
    try{
      const r=await requestOtp(phone.trim());
      setDevCode(r.dev_code);
      setStage("code");
    }catch(e:any){setError(e?.message||"No pudimos enviar el código.")}
    finally{setBusy(false)}
  }

  async function confirmCode(){
    setError(null);
    setBusy(true);
    try{
      const r=await verifyOtp(phone.trim(),code.trim());
      const s={token:r.token,user:r.user};
      setAgentSession(s);
      setSession(s);
      setStage("form");
    }catch(e:any){setError(e?.message||"Código inválido.")}
    finally{setBusy(false)}
  }

  async function finish(){
    if(!session)return;
    if(instagram.trim().length<2){setError("Instagram es requerido para entrar a la cola de verificación.");return}
    setBusy(true);setError(null);
    try{
      const r=await completeOnboarding(token,{
        instagram:instagram.trim(),
        website_link:website.trim()||undefined,
        name:name.trim()||undefined,
      },session);
      setDone(r.message);
    }catch(e:any){setError(e?.message||"No pudimos completar el reclamo.")}
    finally{setBusy(false)}
  }

  return (
    <main className="container" style={{padding:"48px 0 80px",maxWidth:520}}>
      <a href="/" className="brand" style={{display:"inline-block",marginBottom:24,color:"#102033"}}>
        <span className="propWord">Prop</span><span className="omiWord">omi</span>
      </a>
      <h1 style={{fontSize:28,letterSpacing:"-0.5px",margin:"0 0 8px"}}>Reclamá tu perfil</h1>
      <p className="muted" style={{marginBottom:24}}>
        Alguien hizo una oferta real sobre una publicación asociada a tu agencia. Completá estos pasos para verla y gestionarla en Propomi.
      </p>

      {error && <div className="notice" style={{marginBottom:16}}>{error}</div>}
      {done && (
        <div className="notice notice-ok" style={{marginBottom:16}}>
          <Check size={16}/> {done}
          <div style={{marginTop:12}}>
            <a className="primary" href="/agencia" style={{padding:"10px 16px",textDecoration:"none"}}>Ir al panel de agencia</a>
          </div>
        </div>
      )}

      {info && !done && (
        <div className="summarycard" style={{marginBottom:20}}>
          <div className="muted small">Oferta recibida</div>
          <strong>{info.currency} {Number(info.amount).toLocaleString("en-US")}</strong>
          <div>{info.propertyTitle}</div>
          <div className="muted small">{info.propertyZone}{info.agencyName?` · ${info.agencyName}`:""}</div>
        </div>
      )}

      {!done && info && info.status!=="CLAIMED" && (
        <>
          {stage!=="form" && (
            <div className="agentdashpane" style={{gap:12}}>
              <p className="muted small"><LogIn size={14}/> Entrá con el teléfono de la agencia (el mismo de tus publicaciones).</p>
              {stage==="phone" && (
                <>
                  <label>Teléfono<input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="11 5555-0202"/></label>
                  <button className="primary" disabled={busy} onClick={sendCode}>Enviar código</button>
                </>
              )}
              {stage==="code" && (
                <>
                  <label>Código SMS<input value={code} onChange={e=>setCode(e.target.value)} placeholder="6 dígitos"/></label>
                  {devCode && <p className="muted small">Código de desarrollo: {devCode}</p>}
                  <button className="primary" disabled={busy} onClick={confirmCode}>Confirmar</button>
                </>
              )}
            </div>
          )}

          {stage==="form" && session && (
            <div className="agentdashpane" style={{gap:12}}>
              <p className="muted small"><Building2 size={14}/> Sesión: {session.user.phone}</p>
              <label>Nombre de la agencia<input value={name} onChange={e=>setName(e.target.value)}/></label>
              <label>Instagram (requerido)<input value={instagram} onChange={e=>setInstagram(e.target.value)} placeholder="@tuagencia"/></label>
              <label>Sitio web (opcional)<input value={website} onChange={e=>setWebsite(e.target.value)} placeholder="https://..."/></label>
              <button className="primary" disabled={busy} onClick={finish}><Check size={15}/> Reclamar perfil</button>
              <p className="muted small">Después vas a la cola de verificación. El link de esta invitación queda inválido.</p>
            </div>
          )}
        </>
      )}
    </main>
  );
}
