'use client';
import {useState} from 'react';
import {Check,Handshake,Lock,RefreshCw,Unlock,X} from 'lucide-react';
import {Offer,Session} from '../lib/types';
import {counterOffer,mockCompletePayment,offerAction,paymentStatus,revealContact} from '../lib/api';

// Igual criterio que del lado comprador: nada de texto/números libres.
// La contraoferta se arma con presets sobre el monto ofrecido por el
// comprador, no tipeando un valor.
const COUNTER_PRESETS=[3,5,8,12];
const fmt=(n:number)=>Math.round(n).toLocaleString('en-US');

export default function AgentOfferActions({offer,session,onDone}:{offer:Offer;session:Session;onDone:(message:string)=>void}){
  const [pct,setPct]=useState(5);
  const [busy,setBusy]=useState(false);
  const [revealed,setRevealed]=useState<{buyer_name:string;buyer_phone:string;buyer_email?:string}|null>(
    offer.contact_revealed && offer.buyer_name && offer.buyer_phone ? {buyer_name:offer.buyer_name,buyer_phone:offer.buyer_phone,buyer_email:offer.buyer_email} : null
  );
  const [pendingPayment,setPendingPayment]=useState<string|null>(null);
  const [checkoutUrl,setCheckoutUrl]=useState<string|null>(null);
  const counterAmount=Math.round(offer.amount*(1+pct/100));

  async function action(a:'accept'|'reject'|'negotiate'){
    setBusy(true);
    try{await offerAction(offer.id,a,session);onDone(a==='accept'?'Oferta aceptada.':a==='reject'?'Oferta rechazada.':'Negociación iniciada.')}
    finally{setBusy(false)}
  }

  async function counter(){
    setBusy(true);
    try{await counterOffer(offer.id,counterAmount,undefined,session);onDone('Contraoferta enviada.')}
    finally{setBusy(false)}
  }

  async function reveal(){
    setBusy(true);
    try{
      const r=await revealContact(offer.id,session);
      setRevealed({buyer_name:r.buyer_name,buyer_phone:r.buyer_phone,buyer_email:r.buyer_email});
      onDone('Contacto revelado.');
    }catch(e:any){
      if(e?.status===402 && e?.detail?.transaction_id){
        const url=e.detail.checkout_url||null;
        setPendingPayment(e.detail.transaction_id);
        setCheckoutUrl(url);
        if(url){
          // Abrir checkout hosteado sin forzar pop-up blockers: el click del usuario ya abrió el handler.
          try{window.open(url,'_blank','noopener,noreferrer')}catch{}
          onDone('Te redirigimos al pago. Cuando termines, volvé y tocá «Ya pagué».');
        }else{
          onDone('Pago requerido. Todavía no hay checkout real (Lemon sin configurar o modo mock).');
        }
      }else{
        onDone(e?.message||'No se pudo revelar el contacto.');
      }
    }finally{
      setBusy(false);
    }
  }

  async function checkPayment(){
    if(!pendingPayment)return;
    setBusy(true);
    try{
      const s=await paymentStatus(pendingPayment,session);
      if(s.status==='COMPLETED'){
        // ya se cobró (Lemon Squeezy confirmó por webhook) — el reveal ahora
        // solo devuelve el contacto, sin volver a intentar cobrar.
        const r=await revealContact(offer.id,session);
        setRevealed({buyer_name:r.buyer_name,buyer_phone:r.buyer_phone,buyer_email:r.buyer_email});
        setPendingPayment(null);
        setCheckoutUrl(null);
        onDone('Pago confirmado — contacto revelado.');
      }else{
        onDone('Todavía no se confirmó el pago. Probá de nuevo en unos segundos.');
      }
    }catch(e:any){
      onDone(e?.message||'No se pudo verificar el pago.');
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
        setRevealed({buyer_name:r.buyer_name,buyer_phone:r.buyer_phone,buyer_email:r.buyer_email});
        setPendingPayment(null);
        setCheckoutUrl(null);
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
      <div className="quickrow">
        {COUNTER_PRESETS.map(v=>
          <button key={v} className={pct===v?'quickbtn active':'quickbtn'} onClick={()=>setPct(v)}>+{v}%</button>)}
      </div>
      <button className="primary" disabled={busy} onClick={counter}><RefreshCw size={15}/> Contraofertar USD {fmt(counterAmount)}</button>
    </div>

    {revealed ? (
      <div className="reveal-box reveal-box--done">
        <Unlock size={15}/> <strong>{revealed.buyer_name}</strong> · {revealed.buyer_phone}{revealed.buyer_email?` · ${revealed.buyer_email}`:''}
      </div>
    ) : pendingPayment ? (
      <div className="reveal-box reveal-box--pending">
        <Lock size={15}/> Pago pendiente (USD 5) para ver el contacto.
        {checkoutUrl ? (
          <>
            <a className="primary" href={checkoutUrl} target="_blank" rel="noopener noreferrer">
              Abrir pago (Lemon Squeezy)
            </a>
            <button className="secondary" disabled={busy} onClick={checkPayment}>Ya pagué, verificar</button>
            <p className="muted small" style={{margin:0}}>Si cerraste la ventana de pago, volvé a abrir el link y después verificá.</p>
          </>
        ) : (
          <>
            <p className="muted small" style={{margin:0}}>
              No hay URL de checkout. En desarrollo usá «Confirmar pago (dev)». En producción configurá Lemon (ver docs/LEMON_SQUEEZY_CHECKLIST.md).
            </p>
            <button className="secondary" disabled={busy} onClick={confirmMockPayment}>Confirmar pago (dev)</button>
          </>
        )}
      </div>
    ) : (
      <button className="primary" disabled={busy} onClick={reveal}><Lock size={15}/> Revelar contacto</button>
    )}
  </div>
}
