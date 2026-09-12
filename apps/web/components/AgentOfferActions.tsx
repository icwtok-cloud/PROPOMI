'use client';
import {useState} from 'react';
import {Check,Handshake,Lock,RefreshCw,Unlock,X} from 'lucide-react';
import {Offer,Session} from '../lib/types';
import {counterOffer,mockCompletePayment,offerAction,revealContact} from '../lib/api';

export default function AgentOfferActions({offer,session,onDone}:{offer:Offer;session:Session;onDone:(message:string)=>void}){
  const [amount,setAmount]=useState(String(Math.round(offer.amount*1.03)));
  const [busy,setBusy]=useState(false);
  const [revealed,setRevealed]=useState<{buyer_name:string;buyer_phone:string}|null>(
    offer.contact_revealed && offer.buyer_name && offer.buyer_phone ? {buyer_name:offer.buyer_name,buyer_phone:offer.buyer_phone} : null
  );
  const [pendingPayment,setPendingPayment]=useState<string|null>(null);

  async function action(a:'accept'|'reject'|'negotiate'){
    setBusy(true);
    try{await offerAction(offer.id,a,session);onDone(a==='accept'?'Oferta aceptada.':a==='reject'?'Oferta rechazada.':'Negociación iniciada.')}
    finally{setBusy(false)}
  }

  async function counter(){
    setBusy(true);
    try{await counterOffer(offer.id,Number(amount),undefined,session);onDone('Contraoferta enviada.')}
    finally{setBusy(false)}
  }

  async function reveal(){
    setBusy(true);
    try{
      const r=await revealContact(offer.id,session);
      setRevealed({buyer_name:r.buyer_name,buyer_phone:r.buyer_phone});
      onDone('Contacto revelado.');
    }catch(e:any){
      if(e?.status===402 && e?.detail?.transaction_id){
        setPendingPayment(e.detail.transaction_id);
        onDone(e.message||'Se requiere pago para revelar este contacto.');
      }else{
        onDone(e?.message||'No se pudo revelar el contacto.');
      }
    }finally{
      setBusy(false);
    }
  }

  async function confirmMockPayment(){
    if(!pendingPayment)return;
    setBusy(true);
    try{
      const r=await mockCompletePayment(pendingPayment,session);
      if(r.buyer_name && r.buyer_phone){
        setRevealed({buyer_name:r.buyer_name,buyer_phone:r.buyer_phone});
        setPendingPayment(null);
        onDone('Pago confirmado (modo desarrollo) — contacto revelado.');
      }
    }finally{
      setBusy(false);
    }
  }

  return <div className="agent-actions">
    <button className="secondary" disabled={busy} onClick={()=>action('accept')}><Check size={15}/> Aceptar</button>
    <button className="secondary" disabled={busy} onClick={()=>action('reject')}><X size={15}/> Rechazar</button>
    <button className="secondary" disabled={busy} onClick={()=>action('negotiate')}><Handshake size={15}/> Negociar</button>
    <div className="counterline">
      <input aria-label="Monto de contraoferta" value={amount} onChange={e=>setAmount(e.target.value)} inputMode="numeric"/>
      <button className="primary" disabled={busy||Number(amount)<=0} onClick={counter}><RefreshCw size={15}/> Contraofertar</button>
    </div>

    {revealed ? (
      <div className="reveal-box reveal-box--done">
        <Unlock size={15}/> <strong>{revealed.buyer_name}</strong> · {revealed.buyer_phone}
      </div>
    ) : pendingPayment ? (
      <div className="reveal-box reveal-box--pending">
        <Lock size={15}/> Pago pendiente para ver el contacto.
        <button className="primary" disabled={busy} onClick={confirmMockPayment}>Confirmar pago (dev)</button>
      </div>
    ) : (
      <button className="primary" disabled={busy} onClick={reveal}><Lock size={15}/> Revelar contacto</button>
    )}
  </div>
}
