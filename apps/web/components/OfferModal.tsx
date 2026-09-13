'use client';
import {useState,useRef,useEffect} from 'react';
import {Property,Intent,Session} from '../lib/types';
import {createOffer,saveIntent,trackEvent,getOrCreateBuyerSession,getBuyerProfile,setBuyerProfile,requestOtp,verifyOtpBuyer,setBuyerSession,linkGoogleIdentity} from '../lib/api';
import {renderGoogleButton} from '../lib/google';

const CAPITAL_BUCKETS=[
  {label:'Menos de USD 50.000',value:30000},
  {label:'USD 50.000 – 80.000',value:50000},
  {label:'USD 80.000 – 120.000',value:80000},
  {label:'Más de USD 120.000',value:120000},
];
const PAYMENT_FORMS=[
  {label:'Contado',value:'CASH'},
  {label:'Mixta',value:'MIXED'},
  {label:'Financiación',value:'FINANCING'},
];
const TIMEFRAMES=['0-30 días','30-60 días','60-90 días','Más de 90 días'];
const CONDITIONS=[
  'Sujeto a aprobación de crédito',
  'Necesito escritura rápida',
  'Busco flexibilidad de mudanza',
  'Evalúo otras propiedades',
  'Sin condicionantes particulares',
];
const STEP_COUNT=5;
const fmt=(n:number)=>Math.round(n).toLocaleString('en-US');

// Todo este flujo es selección (slider + botones). El único texto libre que
// existía acá (monto, capital, comentario) se reemplazó por controles
// cerrados para que sea imposible deslizar datos de contacto entre las
// partes por este medio. El backend además sigue validando el comentario
// como defensa en profundidad, pero ya no depende de esa validación porque
// el usuario nunca escribe texto libre.
export default function OfferModal({p,onClose,onDone}:{p:Property;onClose:()=>void;onDone:(msg:string)=>void}){
  const [step,setStep]=useState(1);
  const [pct,setPct]=useState(8); // % por debajo del precio pedido
  const [capitalIdx,setCapitalIdx]=useState<number|null>(null);
  const [paymentIdx,setPaymentIdx]=useState<number|null>(null);
  const [timeframe,setTimeframe]=useState<string|null>(null);
  const [conditions,setConditions]=useState<string[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<string|null>(null);

  // Etapa 2 / sección 6.2.1: verificación de identidad, recién en este
  // último paso — nunca antes, para no reintroducir la fricción que el
  // wizard de pasos cortos está diseñado para evitar.
  const initialProfile=getBuyerProfile();
  const [phoneVerified,setPhoneVerified]=useState(!!initialProfile?.phoneVerified);
  const [googleVerified,setGoogleVerified]=useState(!!initialProfile?.googleVerified);
  const [otpSent,setOtpSent]=useState(false);
  const [otpCode,setOtpCode]=useState('');
  const [otpBusy,setOtpBusy]=useState(false);
  const [otpError,setOtpError]=useState<string|null>(null);
  const [googleError,setGoogleError]=useState<string|null>(null);
  const googleBtnRef=useRef<HTMLDivElement|null>(null);

  function toggleCondition(c:string){setConditions(prev=>prev.includes(c)?prev.filter(x=>x!==c):[...prev,c])}

  async function sendOtp(){
    const profile=getBuyerProfile();
    if(!profile)return;
    setOtpBusy(true);setOtpError(null);
    try{await requestOtp(profile.phone);setOtpSent(true)}
    catch(e:any){setOtpError(e?.message||'No pudimos enviar el código. Intentá de nuevo.')}
    finally{setOtpBusy(false)}
  }

  async function confirmOtp(){
    const profile=getBuyerProfile();
    if(!profile||otpCode.trim().length<4)return;
    setOtpBusy(true);setOtpError(null);
    try{
      const r=await verifyOtpBuyer(profile.phone,otpCode.trim());
      setBuyerSession({token:r.token,user:r.user});
      setBuyerProfile({...profile,phoneVerified:true});
      setPhoneVerified(true);
    }catch(e:any){setOtpError(e?.message||'Código incorrecto o vencido.')}
    finally{setOtpBusy(false)}
  }

  async function onGoogleToken(idToken:string){
    setGoogleError(null);
    try{
      const session=await getOrCreateBuyerSession();
      if(!session)throw new Error('Verificá tu celular primero.');
      const r=await linkGoogleIdentity(idToken,session);
      const profile=getBuyerProfile();
      if(profile)setBuyerProfile({...profile,email:r.email,googleVerified:true});
      setGoogleVerified(true);
    }catch(e:any){setGoogleError(e?.message||'No pudimos confirmar tu cuenta de Google.')}
  }

  useEffect(()=>{
    if(step!==5||!phoneVerified||googleVerified)return;
    if(!googleBtnRef.current)return;
    renderGoogleButton(googleBtnRef.current,onGoogleToken).catch(e=>setGoogleError(e?.message||'Google Sign-In no está disponible.'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[step,phoneVerified,googleVerified]);

  const amount=Math.round(p.price*(1-pct/100));

  async function send(){
    if(capitalIdx===null||paymentIdx===null||!timeframe)return;
    const profile=getBuyerProfile();
    if(!profile){setError('Nos falta tu contacto. Cerrá este paso y volvé a intentar.');return}
    setBusy(true);
    setError(null);
    try{
      const session:Session|null=await getOrCreateBuyerSession();
      const capital=CAPITAL_BUCKETS[capitalIdx].value;
      const payment_form=PAYMENT_FORMS[paymentIdx].value;
      const comment=conditions.length?conditions.join(', '):undefined; // frases predefinidas, nunca texto libre
      const data:Intent={offer:true,budget:p.price,capital,financing:payment_form==='FINANCING'?'YES':'NO',timeframe,alternatives:true,comment};
      await createOffer({property_id:p.id,amount,payment_form,capital,timeframe,comment,buyer_name:profile.name,buyer_phone:profile.phone,buyer_email:profile.email},session);
      await saveIntent(p.id,'OFFER',8,data,session);
      await trackEvent('offer_created',p.id,{amount},session);
      onDone('Oferta enviada. Tu nombre y teléfono quedan ocultos: el agente solo los ve si decide revelar el contacto.');
    }catch(e:any){
      setError(e?.message||'No se pudo enviar la oferta. Intentá de nuevo.');
    }finally{
      setBusy(false);
    }
  }

  return <div className="modalback">
    <div className="modal offerwizard">
      <div className="modalhead">
        <div><span className="eyebrow">Negociación</span><h2>Proponer un precio</h2>
          <p className="muted">{p.title} · USD {fmt(p.price)}</p></div>
        <button className="close" onClick={onClose}>×</button>
      </div>

      <div className="wizprogress">{Array.from({length:STEP_COUNT}).map((_,i)=><span key={i} className={i<step?'done':''}/>)}</div>

      {step===1&&<div className="wizstep">
        <div className="qlabel">¿Cuánto querés ofrecer?</div>
        <div className="qhelp">Ajustá el control — sin escribir montos a mano.</div>
        <div className="sliderbox">
          <div className="slidervalue">USD {fmt(amount)}</div>
          <div className="sliderref">{pct===0?'Precio pedido':`${pct}% por debajo del pedido (USD ${fmt(p.price)})`}</div>
          <input type="range" min={0} max={15} step={1} value={pct} onChange={e=>setPct(Number(e.target.value))}/>
          <div className="quickrow">
            {[0,5,8,12,15].map(v=>
              <button key={v} className={pct===v?'quickbtn active':'quickbtn'} onClick={()=>setPct(v)}>{v===0?'Pedido':`-${v}%`}</button>)}
          </div>
        </div>
        <div className="wizactions modalactions">
          <button className="secondary" onClick={onClose}>Cancelar</button>
          <button className="primary" onClick={()=>setStep(2)}>Continuar</button>
        </div>
      </div>}

      {step===2&&<div className="wizstep">
        <div className="qlabel">¿Con cuánto capital disponible contás?</div>
        <div className="qhelp small">Es un rango, no necesitás el monto exacto.</div>
        <div className="chipgrid">{CAPITAL_BUCKETS.map((c,i)=>
          <button key={c.label} className={capitalIdx===i?'wchip selected':'wchip'} onClick={()=>setCapitalIdx(i)}>{c.label}</button>)}
        </div>
        <div className="qlabel">¿Cómo pensás pagar?</div>
        <div className="chipgrid triple">{PAYMENT_FORMS.map((f,i)=>
          <button key={f.label} className={paymentIdx===i?'wchip selected':'wchip'} onClick={()=>setPaymentIdx(i)}>{f.label}</button>)}
        </div>
        <div className="wizactions modalactions">
          <button className="secondary" onClick={()=>setStep(1)}>Volver</button>
          <button className="primary" disabled={capitalIdx===null||paymentIdx===null} onClick={()=>setStep(3)}>Continuar</button>
        </div>
      </div>}

      {step===3&&<div className="wizstep">
        <div className="qlabel">¿En qué plazo podrías cerrar la operación?</div>
        <div className="chipgrid">{TIMEFRAMES.map(t=>
          <button key={t} className={timeframe===t?'wchip selected':'wchip'} onClick={()=>setTimeframe(t)}>{t}</button>)}
        </div>
        <div className="qlabel">¿Hay algo que quieras aclarar?</div>
        <div className="qhelp small">Opcional · elegí todas las que apliquen</div>
        <div className="chipgrid">{CONDITIONS.map(c=>
          <button key={c} className={(conditions.includes(c)?'wchip selected':'wchip')+(c==='Sin condicionantes particulares'?' wide':'')} onClick={()=>toggleCondition(c)}>{c}</button>)}
        </div>
        <div className="wizactions modalactions">
          <button className="secondary" onClick={()=>setStep(2)}>Volver</button>
          <button className="primary" disabled={!timeframe} onClick={()=>setStep(4)}>Continuar</button>
        </div>
      </div>}

      {step===4&&<div className="wizstep">
        <div className="qlabel">Así queda tu propuesta</div>
        <div className="summarycard">
          <div className="summaryrow"><span>Monto ofertado</span><b>USD {fmt(amount)}</b></div>
          <div className="summaryrow"><span>Capital disponible</span><b>{capitalIdx!==null?CAPITAL_BUCKETS[capitalIdx].label:'—'}</b></div>
          <div className="summaryrow"><span>Forma de pago</span><b>{paymentIdx!==null?PAYMENT_FORMS[paymentIdx].label:'—'}</b></div>
          <div className="summaryrow"><span>Plazo</span><b>{timeframe}</b></div>
          <div className="summaryrow"><span>Condicionantes</span><b>{conditions.length?conditions.join(', '):'Ninguno'}</b></div>
        </div>
        <div className="notice">🔒 Tu nombre y teléfono quedan ocultos para el agente hasta que decida revelar el contacto (pagando o con su suscripción).</div>
        <div className="wizactions modalactions">
          <button className="secondary" onClick={()=>setStep(3)}>Volver</button>
          <button className="primary" onClick={()=>setStep(5)}>Continuar</button>
        </div>
      </div>}

      {step===5&&<div className="wizstep">
        <div className="qlabel">Confirmá que sos vos</div>
        <div className="qhelp small">Último paso — esto nos permite avisarte cuando el agente responda y evitar propuestas falsas.</div>

        <div className="summarycard" style={{marginTop:10}}>
          <div className="summaryrow">
            <span>Celular {initialProfile?.phone}</span>
            <b>{phoneVerified?'✅ Verificado':''}</b>
          </div>
          {!phoneVerified&&<div style={{marginTop:10}}>
            {!otpSent
              ?<button className="secondary" disabled={otpBusy} onClick={sendOtp}>{otpBusy?'Enviando…':'Enviar código por SMS'}</button>
              :<div className="formgrid" style={{gridTemplateColumns:'1fr auto',gap:8,alignItems:'center'}}>
                <input value={otpCode} onChange={e=>setOtpCode(e.target.value)} placeholder="Código de 6 dígitos" inputMode="numeric" maxLength={6}/>
                <button className="primary" disabled={otpBusy||otpCode.trim().length<4} onClick={confirmOtp}>{otpBusy?'Verificando…':'Verificar'}</button>
              </div>}
            {otpError&&<div className="notice notice-error" style={{marginTop:8}}>{otpError}</div>}
          </div>}
        </div>

        {phoneVerified&&<div className="summarycard" style={{marginTop:12}}>
          <div className="summaryrow">
            <span>Cuenta de Google</span>
            <b>{googleVerified?'✅ Confirmada':''}</b>
          </div>
          {!googleVerified&&<div style={{marginTop:10}}>
            <div ref={googleBtnRef}/>
            {googleError&&<div className="notice notice-error" style={{marginTop:8}}>{googleError}</div>}
          </div>}
        </div>}

        {error && <div className="notice notice-error" style={{marginTop:12}}>{error}</div>}
        <div className="wizactions modalactions">
          <button className="secondary" onClick={()=>setStep(4)}>Volver</button>
          <button className="primary" disabled={busy||!phoneVerified||!googleVerified} onClick={send}>{busy?'Enviando…':'Enviar oferta'}</button>
        </div>
      </div>}
    </div>
  </div>;
}
