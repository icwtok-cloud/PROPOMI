'use client';
import {useState} from 'react';
import {Property,Intent,Session} from '../lib/types';
import {createOffer,saveIntent,trackEvent,getOrCreateBuyerSession,getBuyerProfile} from '../lib/api';

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
const STEP_COUNT=4;
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

  function toggleCondition(c:string){setConditions(prev=>prev.includes(c)?prev.filter(x=>x!==c):[...prev,c])}

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
        {error && <div className="notice notice-error">{error}</div>}
        <div className="notice">🔒 Tu nombre y teléfono quedan ocultos para el agente hasta que decida revelar el contacto (pagando o con su suscripción).</div>
        <div className="wizactions modalactions">
          <button className="secondary" onClick={()=>setStep(3)}>Volver</button>
          <button className="primary" disabled={busy} onClick={send}>{busy?'Enviando…':'Enviar oferta'}</button>
        </div>
      </div>}
    </div>
  </div>;
}
