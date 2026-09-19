'use client';
import {useState} from 'react';
import {Lock,Unlock} from 'lucide-react';
import {Lead,Session} from '../lib/types';
import {mockCompletePayment,paymentStatus,revealLeadContact} from '../lib/api';

// Espejo reducido de AgentOfferActions: los leads (consulta/visita) todavía
// no tienen accept/reject/negotiate/counter en el backend (fuera de alcance
// a propósito hasta definir cómo queda la card en este panel) — por ahora
// la única acción disponible es revelar el contacto, igual que en ofertas.
export default function AgentLeadActions({lead,session,onDone}:{lead:Lead;session:Session;onDone:(message:string)=>void}){
  const [busy,setBusy]=useState(false);
  const [revealed,setRevealed]=useState<{buyer_name:string;buyer_phone:string;buyer_email?:string}|null>(
    lead.contact_revealed && lead.buyer_name && lead.buyer_phone ? {buyer_name:lead.buyer_name,buyer_phone:lead.buyer_phone,buyer_email:lead.buyer_email} : null
  );
  const [pendingPayment,setPendingPayment]=useState<string|null>(null);
  const [checkoutUrl,setCheckoutUrl]=useState<string|null>(null);

  async function reveal(){
    setBusy(true);
    try{
      const r=await revealLeadContact(lead.id,session);
      setRevealed({buyer_name:r.buyer_name,buyer_phone:r.buyer_phone,buyer_email:r.buyer_email});
      onDone('Contacto revelado.');
    }catch(e:any){
      if(e?.status===402 && e?.detail?.transaction_id){
        const url=e.detail.checkout_url||null;
        setPendingPayment(e.detail.transaction_id);
        setCheckoutUrl(url);
        if(url){
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
        const r=await revealLeadContact(lead.id,session);
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
    {revealed ? (
      <div className="reveal-box reveal-box--done">
        <Unlock size={15}/> <strong>{revealed.buyer_name}</strong> · {revealed.buyer_phone}{revealed.buyer_email?` · ${revealed.buyer_email}`:''}
      </div>
    ) : pendingPayment ? (
      <div className="reveal-box reveal-box--pending">
        <Lock size={15}/> Pago pendiente para ver el contacto.
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
