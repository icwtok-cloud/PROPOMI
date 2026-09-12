'use client';import {useState} from 'react';import {Property,Intent,Session} from '../lib/types';import {createOffer,saveIntent,trackEvent,getOrCreateBuyerSession} from '../lib/api';
export default function OfferModal({p,onClose,onDone}:{p:Property;onClose:()=>void;onDone:(msg:string)=>void}){
  const [buyerName,setBuyerName]=useState('');
  const [buyerPhone,setBuyerPhone]=useState('');
  const [amount,setAmount]=useState(String(Math.round(p.price*.92)));
  const [capital,setCapital]=useState('80000');
  const [form,setForm]=useState('MIXED');
  const [time,setTime]=useState('30-60 días');
  const [comment,setComment]=useState('');
  const [error,setError]=useState<string|null>(null);
  const [busy,setBusy]=useState(false);

  async function send(){
    setError(null);
    if(buyerName.trim().length<2){setError('Ingresá tu nombre y apellido.');return}
    if(buyerPhone.trim().length<6){setError('Ingresá un teléfono de contacto válido.');return}
    setBusy(true);
    try{
      const session:Session|null=await getOrCreateBuyerSession();
      const data:Intent={offer:true,budget:p.price,capital:Number(capital),financing:form==='FINANCING'?'YES':'NO',timeframe:time,alternatives:true,comment};
      await createOffer({property_id:p.id,amount:Number(amount),payment_form:form,capital:Number(capital),timeframe:time,comment,buyer_name:buyerName.trim(),buyer_phone:buyerPhone.trim()},session);
      await saveIntent(p.id,'OFFER',8,data,session);
      await trackEvent('offer_created',p.id,{amount:Number(amount)},session);
      onDone('Oferta enviada. Tu nombre y teléfono quedan ocultos: el agente solo los ve si decide revelar el contacto.');
    }catch(e:any){
      // El backend rechaza con 400 si el comentario contiene un teléfono, email
      // o usuario de redes — mostramos el motivo tal cual lo explica la API.
      setError(e?.message||'No se pudo enviar la oferta. Revisá los datos e intentá de nuevo.');
    }finally{
      setBusy(false);
    }
  }

  return <div className="modalback"><div className="modal">
    <div className="modalhead">
      <div><span className="eyebrow">Negociación</span><h2>Proponer un precio</h2><p className="muted">{p.title} · USD {p.price.toLocaleString('en-US')}</p></div>
      <button className="close" onClick={onClose}>×</button>
    </div>
    <div className="formgrid">
      <label>Nombre y apellido<input value={buyerName} onChange={e=>setBuyerName(e.target.value)} placeholder="Ej: María Fernández"/></label>
      <label>Celular<input value={buyerPhone} onChange={e=>setBuyerPhone(e.target.value)} placeholder="Ej: 11 5555 5555" inputMode="tel"/></label>
      <label>Monto de oferta<input value={amount} onChange={e=>setAmount(e.target.value)}/></label>
      <label>Capital disponible<input value={capital} onChange={e=>setCapital(e.target.value)}/></label>
      <label>Forma de pago<select value={form} onChange={e=>setForm(e.target.value)}><option value="MIXED">Mixta</option><option value="CASH">Contado</option><option value="FINANCING">Financiación</option></select></label>
      <label>Plazo<select value={time} onChange={e=>setTime(e.target.value)}><option>0-30 días</option><option>30-60 días</option><option>60-90 días</option><option>Más de 90 días</option></select></label>
    </div>
    <label>Comentario opcional<textarea value={comment} onChange={e=>setComment(e.target.value)} placeholder="Condiciones o contexto (sin teléfonos, emails ni links: se rechaza automáticamente)"/></label>
    {error && <div className="notice notice-error">{error}</div>}
    <div className="notice">🔒 Tu nombre y teléfono quedan ocultos para el agente hasta que decida revelar el contacto (pagando o con su suscripción). Nunca los compartimos por fuera de este flujo.</div>
    <div className="modalactions">
      <button className="secondary" onClick={onClose}>Cancelar</button>
      <button className="primary" disabled={busy} onClick={send}>{busy?'Enviando…':'Enviar oferta'}</button>
    </div>
  </div></div>
}
