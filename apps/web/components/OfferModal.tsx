'use client';import {useMemo,useState} from 'react';import {Property,Intent,Session} from '../lib/types';import {createOffer,saveIntent,trackEvent,getOrCreateBuyerSession} from '../lib/api';import {ShieldCheck,ChevronLeft,ChevronRight} from 'lucide-react';

const CAPITAL_STEPS=[30000,60000,90000,120000,150000];
const PAYMENT_FORMS=[['CASH','Contado'],['FINANCING','Financiación'],['MIXED','Mixta']] as const;
const TIMEFRAMES=['0-30 días','30-60 días','60-90 días','Más de 90 días'];
const CONDITIONS=['Mudanza rápida','Tengo otra propiedad para entregar/vender','Busco financiación bancaria','Sin condicionantes particulares'];
const DISCOUNTS=[0,-5,-10,-15];

// Todo el flujo entra en 3 pantallas: 1) los dos números (precio y capital,
// donde la persona quiere sentir control fino vía slider), 2) preferencias
// rápidas de un solo toque (pago, plazo, condiciones) y 3) datos de contacto
// + confirmación en la misma pantalla. Menos pasos = menos fricción/abandono.
const PANES=['Tu oferta','Preferencias','Contacto'] as const;

export default function OfferModal({p,onClose,onDone}:{p:Property;onClose:()=>void;onDone:(msg:string)=>void}){
  const [pane,setPane]=useState(0);
  const [discount,setDiscount]=useState(-5);
  const [capital,setCapital]=useState(90000);
  const [form,setForm]=useState<'CASH'|'FINANCING'|'MIXED'>('MIXED');
  const [time,setTime]=useState(TIMEFRAMES[1]);
  const [conditions,setConditions]=useState<string[]>([]);
  const [buyerName,setBuyerName]=useState('');
  const [buyerPhone,setBuyerPhone]=useState('');
  const [buyerEmail,setBuyerEmail]=useState('');
  const [error,setError]=useState<string|null>(null);
  const [busy,setBusy]=useState(false);

  const amount=useMemo(()=>Math.round(p.price*(1+discount/100)),[p.price,discount]);
  const capitalLabel=capital>=150000?'USD 150.000+':`USD ${capital.toLocaleString('en-US')}`;
  const comment=useMemo(()=>conditions.length?conditions.join(' · '):'Sin condicionantes particulares',[conditions]);
  const paymentLabel=PAYMENT_FORMS.find(([v])=>v===form)?.[1];

  function toggleCondition(c:string){
    if(c==='Sin condicionantes particulares'){setConditions(['Sin condicionantes particulares']);return}
    setConditions(prev=>{
      const withoutNone=prev.filter(x=>x!=='Sin condicionantes particulares');
      return withoutNone.includes(c)?withoutNone.filter(x=>x!==c):[...withoutNone,c];
    });
  }

  function next(){setError(null);setPane(s=>Math.min(s+1,PANES.length-1))}
  function back(){setError(null);setPane(s=>Math.max(s-1,0))}

  async function send(){
    setError(null);
    if(buyerName.trim().length<2){setError('Ingresá tu nombre y apellido.');return}
    if(buyerPhone.trim().length<6){setError('Ingresá un teléfono de contacto válido.');return}
    setBusy(true);
    try{
      const session:Session|null=await getOrCreateBuyerSession();
      const data:Intent={offer:true,budget:p.price,capital,financing:form==='FINANCING'?'YES':'NO',timeframe:time,alternatives:conditions.includes('Tengo otra propiedad para entregar/vender'),comment};
      await createOffer({property_id:p.id,amount,payment_form:form,capital,timeframe:time,comment,buyer_name:buyerName.trim(),buyer_phone:buyerPhone.trim(),buyer_email:buyerEmail.trim()||undefined},session);
      await saveIntent(p.id,'OFFER',8,data,session);
      await trackEvent('offer_created',p.id,{amount},session);
      onDone('Oferta enviada. Tus datos quedan protegidos: el agente solo los ve si decide revelar el contacto, y nunca se comparten para spam.');
    }catch(e:any){
      setError(e?.message||'No se pudo enviar la oferta. Revisá los datos e intentá de nuevo.');
    }finally{
      setBusy(false);
    }
  }

  return <div className="modalback"><div className="modal wizard">
    <div className="modalhead">
      <div><span className="eyebrow">Negociación</span><h2>Proponer un precio</h2><p className="muted">{p.title} · USD {p.price.toLocaleString('en-US')}</p></div>
      <button className="close" onClick={onClose}>×</button>
    </div>

    <div className="wizardsteps">{PANES.map((s,i)=><div key={s} className={i===pane?'wizarddot active':i<pane?'wizarddot done':'wizarddot'}/>)}</div>

    {pane===0 && <div className="wizardpane">
      <h3>¿Cuánto querés ofertar?</h3>
      <div className="pricebig">USD {amount.toLocaleString('en-US')}</div>
      <p className="muted small">Sobre el precio de lista de USD {p.price.toLocaleString('en-US')} ({discount===0?'precio de lista':`${discount}%`})</p>
      <div className="chiprow">{DISCOUNTS.map(d=><button key={d} className={d===discount?'chip active':'chip'} onClick={()=>setDiscount(d)}>{d===0?'Precio de lista':`${d}%`}</button>)}</div>
      <input type="range" min={-20} max={0} step={1} value={discount} onChange={e=>setDiscount(Number(e.target.value))} className="wizardslider"/>

      <h3 className="pane-subhead">¿Con cuánto capital disponible contás?</h3>
      <div className="pricebig">{capitalLabel}</div>
      <div className="chiprow">{CAPITAL_STEPS.map(c=><button key={c} className={c===capital?'chip active':'chip'} onClick={()=>setCapital(c)}>{c>=150000?'USD 150.000+':`USD ${(c/1000)}.000`}</button>)}</div>
      <input type="range" min={30000} max={150000} step={30000} value={capital} onChange={e=>setCapital(Number(e.target.value))} className="wizardslider"/>
    </div>}

    {pane===1 && <div className="wizardpane">
      <h3>¿Cómo pensás pagar?</h3>
      <div className="chiprow big">{PAYMENT_FORMS.map(([v,label])=><button key={v} className={v===form?'chip active':'chip'} onClick={()=>setForm(v)}>{label}</button>)}</div>

      <h3 className="pane-subhead">¿En qué plazo te gustaría avanzar?</h3>
      <div className="chiprow big">{TIMEFRAMES.map(t=><button key={t} className={t===time?'chip active':'chip'} onClick={()=>setTime(t)}>{t}</button>)}</div>

      <h3 className="pane-subhead">¿Alguna condición para tu compra?</h3>
      <div className="chiprow big wrap">{CONDITIONS.map(c=><button key={c} className={conditions.includes(c)?'chip active':'chip'} onClick={()=>toggleCondition(c)}>{c}</button>)}</div>
    </div>}

    {pane===2 && <div className="wizardpane">
      <div className="offersummary">USD {amount.toLocaleString('en-US')} · {paymentLabel} · {time}</div>
      <h3>Tus datos de contacto</h3>
      <p className="muted small">Quedan ocultos para el agente hasta que decida revelar el contacto.</p>
      <div className="formgrid">
        <label>Nombre y apellido<input value={buyerName} onChange={e=>setBuyerName(e.target.value)} placeholder="Ej: María Fernández"/></label>
        <label>Celular<input value={buyerPhone} onChange={e=>setBuyerPhone(e.target.value)} placeholder="Ej: 11 5555 5555" inputMode="tel"/></label>
        <label>Email (opcional)<input value={buyerEmail} onChange={e=>setBuyerEmail(e.target.value)} placeholder="Ej: maria@email.com" inputMode="email"/></label>
      </div>
      <div className="notice"><ShieldCheck size={15}/> Tus datos se resguardan por seguridad: el agente solo los ve si decide revelar el contacto (pagando o con su suscripción), y nunca los usamos para enviarte spam ni se comparten fuera de este flujo.</div>
    </div>}

    {error && <div className="notice notice-error">{error}</div>}

    <div className="modalactions">
      {pane===0
        ? <button className="secondary" onClick={onClose}>Cancelar</button>
        : <button className="secondary" onClick={back}><ChevronLeft size={16}/> Atrás</button>}
      {pane<PANES.length-1
        ? <button className="primary" onClick={next}>Siguiente <ChevronRight size={16}/></button>
        : <button className="primary" disabled={busy} onClick={send}>{busy?'Enviando…':'Enviar oferta'}</button>}
    </div>
  </div></div>
}
