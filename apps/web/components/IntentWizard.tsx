'use client';
import {useState,useRef,useEffect} from 'react';
import {Property,Intent,Session} from '../lib/types';
import {createOffer,createLead,saveIntent,trackEvent,getOrCreateBuyerSession,getBuyerProfile,setBuyerProfile,requestOtp,verifyOtpBuyer,setBuyerSession,linkGoogleIdentity,getOfferOrigin} from '../lib/api';
import {renderGoogleButton} from '../lib/google';

export type WizardMode='offer'|'question'|'visit';

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
const VISIT_SLOTS=[
  {label:'8 a 12hs',value:'08-12'},
  {label:'12 a 16hs',value:'12-16'},
  {label:'16 a 20hs',value:'16-20'},
];
const STEP_COUNT=5;
const fmt=(n:number)=>Math.round(n).toLocaleString('en-US');

function buildVisitDays(){
  const days=[];
  const labels=['Domingo','Lunes','Martes','Miércoles','Jueves','Viernes','Sábado'];
  for(let i=0;i<7;i++){
    const d=new Date();
    d.setDate(d.getDate()+i);
    const iso=d.toISOString().slice(0,10);
    let label=labels[d.getDay()]+' '+d.getDate();
    if(i===0)label='Hoy';
    else if(i===1)label='Mañana';
    days.push({iso,label});
  }
  return days;
}

// Wizard unico para las 3 acciones de alta intencion (proponer precio,
// preguntar, pedir visita). Solo cambia el paso 1 segun `mode` — los pasos
// 2-4 (calificacion) son intencionalmente iguales para los tres, para que
// el lead que le llega al agente tenga valor real. El paso 5 (identidad)
// reemplaza por completo al viejo BuyerIdentityModal: nombre, telefono con
// OTP y Google, todo en un mismo lugar, pedido recien al final.
export default function IntentWizard({p,mode,onClose,onDone}:{p:Property;mode:WizardMode;onClose:()=>void;onDone:(msg:string)=>void}){
  const [step,setStep]=useState(1);
  const [pct,setPct]=useState(8);
  const [skipProposal,setSkipProposal]=useState(false);
  const [visitDay,setVisitDay]=useState<string|null>(null);
  const [visitSlot,setVisitSlot]=useState<string|null>(null);
  const [capitalIdx,setCapitalIdx]=useState<number|null>(null);
  const [paymentIdx,setPaymentIdx]=useState<number|null>(null);
  const [timeframe,setTimeframe]=useState<string|null>(null);
  const [conditions,setConditions]=useState<string[]>([]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<string|null>(null);
  const visitDays=useState(buildVisitDays)[0];

  const initialProfile=getBuyerProfile();
  const [buyerName,setBuyerName]=useState(initialProfile?.name||'');
  const [buyerPhone,setBuyerPhone]=useState(initialProfile?.phone||'');
  const [phoneVerified,setPhoneVerified]=useState(!!initialProfile?.phoneVerified);
  const [googleVerified,setGoogleVerified]=useState(!!initialProfile?.googleVerified);
  const [googleSkipped,setGoogleSkipped]=useState(false);
  const [otpSent,setOtpSent]=useState(false);
  const [otpCode,setOtpCode]=useState('');
  const [otpBusy,setOtpBusy]=useState(false);
  const [otpError,setOtpError]=useState<string|null>(null);
  const [googleError,setGoogleError]=useState<string|null>(null);
  const [identityError,setIdentityError]=useState<string|null>(null);
  const googleBtnRef=useRef<HTMLDivElement|null>(null);

  function toggleCondition(c:string){setConditions(prev=>prev.includes(c)?prev.filter(x=>x!==c):[...prev,c])}

  async function sendOtp(){
    setIdentityError(null);
    if(buyerName.trim().length<2){setIdentityError('Ingresá tu nombre y apellido.');return}
    if(buyerPhone.trim().length<6){setIdentityError('Ingresá un celular válido.');return}
    setOtpBusy(true);setOtpError(null);
    try{await requestOtp(buyerPhone.trim());setOtpSent(true)}
    catch(e:any){setOtpError(e?.message||'No pudimos enviar el código. Intentá de nuevo.')}
    finally{setOtpBusy(false)}
  }

  async function confirmOtp(){
    if(otpCode.trim().length<4)return;
    setOtpBusy(true);setOtpError(null);
    try{
      const r=await verifyOtpBuyer(buyerPhone.trim(),otpCode.trim());
      setBuyerSession({token:r.token,user:r.user});
      setBuyerProfile({name:buyerName.trim(),phone:buyerPhone.trim(),phoneVerified:true});
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
    if(step!==5||!phoneVerified||googleVerified||googleSkipped)return;
    if(!googleBtnRef.current)return;
    renderGoogleButton(googleBtnRef.current,onGoogleToken).catch(e=>setGoogleError(e?.message||'Google Sign-In no está disponible.'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[step,phoneVerified,googleVerified,googleSkipped]);

  const hasAmount=mode!=='visit'&&!(mode==='question'&&skipProposal);
  const amount=Math.round(p.price*(1-pct/100));

  function step1Valid(){
    if(mode==='visit')return !!visitDay&&!!visitSlot;
    return true; // offer y question siempre pueden avanzar (question tiene el skip)
  }

  async function send(){
    if(capitalIdx===null||paymentIdx===null||!timeframe)return;
    const profile=getBuyerProfile();
    if(!profile){setError('Nos falta tu contacto. Volvé al paso anterior.');return}
    setBusy(true);
    setError(null);
    try{
      const session:Session|null=await getOrCreateBuyerSession();
      const capital=CAPITAL_BUCKETS[capitalIdx].value;
      const payment_form=PAYMENT_FORMS[paymentIdx].value;
      const comment=conditions.length?conditions.join(', '):undefined;
      const origin=getOfferOrigin();
      if(mode==='offer'){
        const data:Intent={offer:true,budget:p.price,capital,financing:payment_form==='FINANCING'?'YES':'NO',timeframe,alternatives:true,comment};
        await createOffer({property_id:p.id,amount,payment_form,capital,timeframe,comment,buyer_name:profile.name,buyer_phone:profile.phone,buyer_email:profile.email,origin},session);
        await saveIntent(p.id,'OFFER',8,data,session);
        await trackEvent('offer_created',p.id,{amount},session);
        onDone('Oferta enviada. Tu nombre y teléfono quedan ocultos: el agente solo los ve si decide revelar el contacto.');
      }else{
        await createLead({
          property_id:p.id,
          intent_type:mode==='visit'?'VISIT':'QUESTION',
          has_proposal:hasAmount,
          amount:hasAmount?amount:undefined,
          payment_form,capital,timeframe,comment,
          visit_day:mode==='visit'?(visitDay||undefined):undefined,
          visit_slot:mode==='visit'?(visitSlot||undefined):undefined,
          buyer_name:profile.name,buyer_phone:profile.phone,buyer_email:profile.email,origin,
        },session);
        const msg=mode==='visit'
          ?'Solicitud de visita enviada. La agencia puede confirmar o proponer otro horario.'
          :'Consulta enviada. Tus datos siguen ocultos hasta que el agente decida responder.';
        onDone(msg);
      }
    }catch(e:any){
      setError(e?.message||'No se pudo enviar. Intentá de nuevo.');
    }finally{
      setBusy(false);
    }
  }

  const titles:Record<WizardMode,{eyebrow:string;title:string}>={
    offer:{eyebrow:'Negociación',title:'Proponer un precio'},
    question:{eyebrow:'Consulta',title:'Hacer una pregunta'},
    visit:{eyebrow:'Visita',title:'Pedir una visita'},
  };

  return <div className="modalback">
    <div className="modal offerwizard">
      <div className="modalhead">
        <div><span className="eyebrow">{titles[mode].eyebrow}</span><h2>{titles[mode].title}</h2>
          <p className="muted">{p.title} · USD {fmt(p.price)}</p></div>
        <button className="close" onClick={onClose}>×</button>
      </div>

      <div className="wizprogress">{Array.from({length:STEP_COUNT}).map((_,i)=><span key={i} className={i<step?'done':''}/>)}</div>

      {step===1&&mode!=='visit'&&<div className="wizstep">
        <div className="qlabel">¿Cuánto querés ofrecer?</div>
        <div className="qhelp">Ajustá el control — sin escribir montos a mano.</div>
        <div className="sliderbox" style={skipProposal?{opacity:0.4,pointerEvents:'none'}:undefined}>
          <div className="slidervalue">USD {fmt(amount)}</div>
          <div className="sliderref">{pct===0?'Precio pedido':`${pct}% por debajo del pedido (USD ${fmt(p.price)})`}</div>
          <input type="range" min={0} max={15} step={1} value={pct} onChange={e=>setPct(Number(e.target.value))}/>
          <div className="quickrow">
            {[0,5,8,12,15].map(v=>
              <button key={v} className={pct===v?'quickbtn active':'quickbtn'} onClick={()=>setPct(v)}>{v===0?'Pedido':`-${v}%`}</button>)}
          </div>
        </div>
        {mode==='question'&&<div className="wizactions" style={{justifyContent:'center',marginTop:10}}>
          <button className={skipProposal?'quickbtn active':'quickbtn'} onClick={()=>setSkipProposal(!skipProposal)}>Todavía no tengo una propuesta</button>
        </div>}
        <div className="wizactions modalactions">
          <button className="secondary" onClick={onClose}>Cancelar</button>
          <button className="primary" onClick={()=>setStep(2)}>Continuar</button>
        </div>
      </div>}

      {step===1&&mode==='visit'&&<div className="wizstep">
        <div className="qlabel">Decime cuándo te gustaría visitar esta propiedad</div>
        <div className="qhelp small">Elegí un día y una franja horaria.</div>
        <div className="chipgrid">{visitDays.map(d=>
          <button key={d.iso} className={visitDay===d.iso?'wchip selected':'wchip'} onClick={()=>setVisitDay(d.iso)}>{d.label}</button>)}
        </div>
        {visitDay&&<>
          <div className="qlabel">Franja horaria</div>
          <div className="chipgrid triple">{VISIT_SLOTS.map(s=>
            <button key={s.value} className={visitSlot===s.value?'wchip selected':'wchip'} onClick={()=>setVisitSlot(s.value)}>{s.label}</button>)}
          </div>
        </>}
        <div className="wizactions modalactions">
          <button className="secondary" onClick={onClose}>Cancelar</button>
          <button className="primary" disabled={!step1Valid()} onClick={()=>setStep(2)}>Continuar</button>
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
        <div className="qlabel">Así queda tu {mode==='offer'?'propuesta':mode==='visit'?'solicitud de visita':'consulta'}</div>
        <div className="summarycard">
          {hasAmount&&<div className="summaryrow"><span>Monto ofertado</span><b>USD {fmt(amount)}</b></div>}
          {mode==='visit'&&<div className="summaryrow"><span>Visita</span><b>{visitDays.find(d=>d.iso===visitDay)?.label} · {VISIT_SLOTS.find(s=>s.value===visitSlot)?.label}</b></div>}
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

        {!phoneVerified&&<div className="summarycard" style={{marginTop:10}}>
          <div className="qlabel" style={{marginTop:0}}>Nombre y apellido</div>
          <div className="formgrid" style={{gridTemplateColumns:'1fr'}}>
            <input value={buyerName} onChange={e=>setBuyerName(e.target.value)} placeholder="Ej: María Fernández"/>
          </div>
          <div className="qlabel" style={{marginTop:14}}>Celular</div>
          <div className="formgrid" style={{gridTemplateColumns:'1fr'}}>
            <input value={buyerPhone} onChange={e=>setBuyerPhone(e.target.value)} placeholder="Ej: 11 5555 5555" inputMode="tel"/>
          </div>
          {identityError&&<div className="notice notice-error" style={{marginTop:10}}>{identityError}</div>}
          <div style={{marginTop:12}}>
            {!otpSent
              ?<button className="secondary" disabled={otpBusy} onClick={sendOtp}>{otpBusy?'Enviando…':'Enviar código por SMS'}</button>
              :<div className="formgrid" style={{gridTemplateColumns:'1fr auto',gap:8,alignItems:'center'}}>
                <input value={otpCode} onChange={e=>setOtpCode(e.target.value)} placeholder="Código de 6 dígitos" inputMode="numeric" maxLength={6}/>
                <button className="primary" disabled={otpBusy||otpCode.trim().length<4} onClick={confirmOtp}>{otpBusy?'Verificando…':'Verificar'}</button>
              </div>}
            {otpError&&<div className="notice notice-error" style={{marginTop:8}}>{otpError}</div>}
          </div>
        </div>}

        {phoneVerified&&<div className="summarycard" style={{marginTop:10}}>
          <div className="summaryrow">
            <span>Celular {buyerPhone}</span>
            <b>✅ Verificado</b>
          </div>
        </div>}

        {error && <div className="notice notice-error" style={{marginTop:12}}>{error}</div>}
        <div className="wizactions modalactions">
          <button className="secondary" onClick={()=>setStep(4)}>Volver</button>
          <button className="primary" disabled={busy||!phoneVerified} onClick={send}>{busy?'Enviando…':(mode==='offer'?'Enviar oferta':mode==='visit'?'Enviar solicitud':'Enviar consulta')}</button>
        </div>
      </div>}
    </div>
  </div>;
}