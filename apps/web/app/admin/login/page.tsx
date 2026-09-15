'use client';
import {useState} from 'react';
import {useRouter} from 'next/navigation';
import {adminAuthLogin,adminAuthVerifyOtp} from '../../../lib/api';

/**
 * Login admin: usuario+password → OTP SMS → JWT en sessionStorage de la
 * pestaña (sessionStorage, no localStorage: se borra al cerrar la pestaña).
 * El panel /admin solo lee sessionStorage; no hay links públicos a esta ruta
 * desde el resto del sitio.
 */
const ADMIN_TOKEN_KEY = 'propomi-admin-token';
const ADMIN_USER_KEY = 'propomi-admin-user';

export default function AdminLoginPage(){
  const router = useRouter();
  const [username,setUsername]=useState('');
  const [password,setPassword]=useState('');
  const [otp,setOtp]=useState('');
  const [step,setStep]=useState<'creds'|'otp'>('creds');
  const [phoneHint,setPhoneHint]=useState('');
  const [devCode,setDevCode]=useState<string|undefined>();
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState<string|null>(null);

  async function onLogin(){
    setBusy(true);setError(null);
    try{
      const r = await adminAuthLogin(username.trim(), password);
      setPhoneHint(r.phoneHint||'');
      setDevCode(r.dev_code);
      setStep('otp');
    }catch(e:any){
      setError(e?.message||'No se pudo iniciar sesión.');
    }finally{setBusy(false)}
  }

  async function onVerify(){
    setBusy(true);setError(null);
    try{
      const r = await adminAuthVerifyOtp(username.trim(), otp.trim());
      // sessionStorage: vive solo mientras la pestaña esté abierta
      sessionStorage.setItem(ADMIN_TOKEN_KEY, r.token);
      sessionStorage.setItem(ADMIN_USER_KEY, r.user.username);
      router.replace('/admin');
    }catch(e:any){
      setError(e?.message||'Código inválido.');
    }finally{setBusy(false)}
  }

  return (
    <div className="container" style={{padding:'48px 0',maxWidth:420}}>
      <h1 style={{fontSize:24,marginBottom:8}}>Admin Propomi</h1>
      <p className="muted small">Acceso exclusivo del dueño. Requiere usuario, contraseña y OTP por SMS.</p>

      {step==='creds' && (
        <>
          <label>Usuario
            <input value={username} onChange={e=>setUsername(e.target.value)} autoComplete="username"/>
          </label>
          <label>Contraseña
            <input type="password" value={password} onChange={e=>setPassword(e.target.value)} autoComplete="current-password"
              onKeyDown={e=>{if(e.key==='Enter')onLogin()}}/>
          </label>
          <button className="primary" style={{marginTop:12}} disabled={busy||!username||!password} onClick={onLogin}>
            {busy?'Validando…':'Continuar'}
          </button>
        </>
      )}

      {step==='otp' && (
        <>
          <p className="muted small">Enviamos un código al teléfono {phoneHint||'registrado'}.</p>
          {devCode && <p className="notice" style={{marginTop:8}}>Dev code: <b>{devCode}</b></p>}
          <label>Código SMS
            <input value={otp} onChange={e=>setOtp(e.target.value)} inputMode="numeric"
              onKeyDown={e=>{if(e.key==='Enter')onVerify()}}/>
          </label>
          <button className="primary" style={{marginTop:12}} disabled={busy||otp.length<4} onClick={onVerify}>
            {busy?'Verificando…':'Entrar'}
          </button>
          <button className="secondary" style={{marginTop:8,marginLeft:8}} onClick={()=>setStep('creds')}>Volver</button>
        </>
      )}

      {error && <div className="notice" style={{marginTop:12}}>{error}</div>}
    </div>
  );
}
