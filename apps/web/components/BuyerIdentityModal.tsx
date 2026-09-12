'use client';
import {useState} from 'react';
import {ShieldCheck} from 'lucide-react';
import {BuyerProfile} from '../lib/types';
import {setBuyerProfile} from '../lib/api';

// Único lugar de todo el sitio donde se piden nombre/celular al comprador.
// No es un "campo libre" filtrable: es el dato que el propio comprador
// entrega para que LA PLATAFORMA (nunca el agente directamente) lo contacte
// si acepta avanzar. Se guarda una sola vez y se reutiliza siempre.
export default function BuyerIdentityModal({onDone,onClose}:{onDone:(p:BuyerProfile)=>void;onClose:()=>void}){
  const [name,setName]=useState('');
  const [phone,setPhone]=useState('');
  const [error,setError]=useState<string|null>(null);

  function submit(){
    if(name.trim().length<2){setError('Ingresá tu nombre y apellido.');return}
    if(phone.trim().length<6){setError('Ingresá un celular válido.');return}
    const profile:BuyerProfile={name:name.trim(),phone:phone.trim()};
    setBuyerProfile(profile);
    onDone(profile);
  }

  return <div className="modalback">
    <div className="modal offerwizard">
      <div className="modalhead">
        <div><span className="eyebrow">Antes de continuar</span><h2>¿Cómo te contactamos?</h2></div>
        <button className="close" onClick={onClose}>×</button>
      </div>
      <div className="wizstep">
        <div className="qlabel">Nombre y apellido</div>
        <div className="formgrid" style={{gridTemplateColumns:'1fr'}}>
          <input value={name} onChange={e=>setName(e.target.value)} placeholder="Ej: María Fernández"/>
        </div>
        <div className="qlabel" style={{marginTop:14}}>Celular</div>
        <div className="formgrid" style={{gridTemplateColumns:'1fr'}}>
          <input value={phone} onChange={e=>setPhone(e.target.value)} placeholder="Ej: 11 5555 5555" inputMode="tel"/>
        </div>
        {error && <div className="notice notice-error" style={{marginTop:12}}>{error}</div>}
        <div className="notice" style={{marginTop:14}}><ShieldCheck size={14}/> Esto lo ve la agencia recién si acepta tu propuesta y decide revelar el contacto. Te lo pedimos una sola vez.</div>
        <div className="wizactions modalactions">
          <button className="secondary" onClick={onClose}>Cancelar</button>
          <button className="primary" onClick={submit}>Continuar</button>
        </div>
      </div>
    </div>
  </div>;
}
