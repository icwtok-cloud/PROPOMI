'use client';
import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {Search,Check,GitCompare,ShieldCheck,Sparkles,CalendarDays,Handshake,BarChart3,MessageSquare,Lock} from 'lucide-react';
import PropertyCard from '../components/PropertyCard';
import IntentWizard, {WizardMode} from '../components/IntentWizard';
import ComparePanel from '../components/ComparePanel';
import {getProperties,getPropertiesDeduped,trackEvent,listOffers,isOffersRestricted,getOrCreateBuyerSession,captureOfferOriginFromUrl,trackSearchPerformed} from '../lib/api';
import {Property,Offer} from '../lib/types';

const LEVELS=[['Ver',1,'Exploración'],['Guardar',2,'Interés'],['Comparar',3,'Evaluación'],['Preguntar',4,'Consulta'],['Visitar',6,'Intención'],['Ofertar',8,'Decisión'],['Negociar',10,'Negociación'],['Compartir contacto',10,'Contacto']];
const FUNNEL=['Vistas','Guardados','Comparaciones','Consultas','Visitas','Ofertas','Negociaciones','Contacto compartido','Operaciones'];
const PROPERTY_TYPES=['Todos','Departamento','Casa','PH','Oficina','Local','Terreno'];

export default function Home(){
  const [items,setItems]=useState<Property[]>([]);
  const [budget,setBudget]=useState('120000');
  const [zone,setZone]=useState('Palermo');
  const [ptype,setPtype]=useState('Todos');
  const [rooms,setRooms]=useState('2');
  const [parking,setParking]=useState(false);
  const [credit,setCredit]=useState(false);
  const [saved,setSaved]=useState<string[]>([]);
  const [compared,setCompared]=useState<string[]>([]);
  const [wizard,setWizard]=useState<{p:Property;mode:WizardMode}|null>(null);
  const [detail,setDetail]=useState<Property|null>(null);
  const [photoIdx,setPhotoIdx]=useState(0);
  const [offers,setOffers]=useState<Offer[]>([]);
  const [toast,setToast]=useState('');

  useEffect(()=>{captureOfferOriginFromUrl()},[]);
  useEffect(()=>{(async()=>{
    try{
      const items=await getPropertiesDeduped();
      setItems(items);
      try{
        const s=await getOrCreateBuyerSession();
        const offersList=await listOffers(s);
        setOffers(isOffersRestricted(offersList)?[]:(Array.isArray(offersList)?offersList:[]));
      }catch{}
      // Deep link de tracking: /?property=<id>&o=<origen> abre el detalle.
      if(typeof window==='undefined')return;
      const pid=new URLSearchParams(window.location.search).get('property');
      if(!pid)return;
      let found=items.find(p=>p.id===pid)||null;
      if(!found){
        const all=await getProperties();
        const raw=all.find(p=>p.id===pid);
        if(raw){
          found=raw.listingGroupId
            ?(items.find(p=>p.listingGroupId===raw.listingGroupId)||raw)
            :raw;
        }
      }
      if(found){
        setDetail(found);setPhotoIdx(0);
        trackEvent('property_view',found.id,{source:'share_link'});
      }
    }catch{}
  })()},[]);
  useEffect(()=>{if(toast){const t=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(t)}},[toast]);

  const filtered=useMemo(()=>items.filter(p=>(!zone||p.zone===zone)&&(ptype==='Todos'||p.type===ptype)&&(!rooms||rooms==='Todos'||p.rooms===Number(rooms))&&p.price<=Number(budget||Infinity)&&(!parking||p.parking)&&(!credit||p.credit)),[items,zone,ptype,rooms,budget,parking,credit]);
  useEffect(()=>{
    const t=setTimeout(()=>{
      trackSearchPerformed({
        zone:zone||undefined,
        tipo:ptype!=='Todos'?ptype:undefined,
        ambientes:rooms&&rooms!=='Todos'?Number(rooms):undefined,
        precio_max:budget?Number(budget):undefined,
      });
    },600);
    return ()=>clearTimeout(t);
  },[zone,ptype,rooms,budget,parking,credit]);

  const compareItems=items.filter(p=>compared.includes(p.id));

  function ev(name:any,id:string){trackEvent(name,id)}
  function toggleSave(p:Property){const next=saved.includes(p.id)?saved.filter(x=>x!==p.id):[...saved,p.id];setSaved(next);ev('property_save',p.id)}
  function toggleCompare(p:Property){if(compared.includes(p.id))setCompared(compared.filter(x=>x!==p.id));else if(compared.length<4)setCompared([...compared,p.id]);ev('property_compare',p.id)}
  function openDetail(p:Property){setDetail(p);setPhotoIdx(0);ev('property_view',p.id)}
  async function refreshOffers(){
    const r=await listOffers();
    if(isOffersRestricted(r))setOffers([]);
    else setOffers(r);
  }

  return <>
    <nav className="nav"><div className="container navin">
      <a href="#inicio" className="brand">prop<span className="omiWord">omi</span></a>
      <div className="navlinks">
        <a href="#propiedades">Propiedades</a>
        <a href="#como-funciona">Cómo funciona</a>
        <a href="#intencion">Intención</a>
      </div>
      <Link href="/agencia" className="primary" style={{height:38,padding:'0 16px'}}>Soy agente</Link>
    </div></nav>

    <main id="inicio">
      <section className="hero"><div className="container">
        <div className="eyebrow">La capa de intención y decisión inmobiliaria</div>
        <h1>Encontrá una propiedad.<br/><em>Decidí. Proponé. Avanzá.</em></h1>
        <p>Descubrí, compará, evaluá y proponé un precio — sin entregar tus datos antes de tiempo.</p>
        <div className="focus-badge"><ShieldCheck size={14}/> 100% propiedades en venta · cero ruido de alquileres</div>
        <div className="search">
          <div className="field"><label>Dónde</label>
            <select value={zone} onChange={e=>setZone(e.target.value)}>
              <option>Palermo</option><option>Villa Crespo</option><option>Caballito</option><option>Belgrano</option>
            </select></div>
          <div className="field"><label>Tipo de propiedad</label>
            <select value={ptype} onChange={e=>setPtype(e.target.value)}>
              {PROPERTY_TYPES.map(t=><option key={t}>{t}</option>)}
            </select></div>
          <div className="field"><label>Presupuesto máx.</label>
            <input value={budget} onChange={e=>setBudget(e.target.value)} inputMode="numeric" placeholder="USD"/></div>
          <div className="field"><label>Ambientes</label>
            <select value={rooms} onChange={e=>setRooms(e.target.value)}>
              <option>1</option><option>2</option><option>3</option><option>Todos</option>
            </select></div>
          <button className="searchbtn" aria-label="Buscar" onClick={()=>document.getElementById('propiedades')?.scrollIntoView({behavior:'smooth'})}><Search size={19}/></button>
        </div>
        <div className="hero-note">
          <span><ShieldCheck size={15}/> Datos privados por defecto</span>
          <span><Sparkles size={15}/> Intención progresiva</span>
          <span><Handshake size={15}/> Negociación estructurada</span>
        </div>
      </div></section>

      <section className="section" id="propiedades"><div className="container">
        <div className="sectionhead">
          <div><div className="eyebrow">Fase 1 · Discovery + Decision</div><h2>Propiedades que tienen sentido para vos</h2>
            <p className="muted">{filtered.length} compatibles con tus criterios actuales.</p></div>
          <div className="filterrow">
            <button className={parking?'chip active':'chip'} onClick={()=>setParking(!parking)}>Cochera</button>
            <button className={credit?'chip active':'chip'} onClick={()=>setCredit(!credit)}>Apto crédito</button>
            <button className="chip">Balcón</button>
          </div>
        </div>
        <div className="grid">{filtered.map(p=>
          <PropertyCard key={p.id} p={p} saved={saved.includes(p.id)} compared={compared.includes(p.id)}
            onSave={()=>toggleSave(p)} onCompare={()=>toggleCompare(p)}
            onOffer={()=>setWizard({p,mode:'offer'})} onView={()=>openDetail(p)}/>)}
        </div>
        {filtered.length===0&&<div className="empty">No encontramos propiedades con estos criterios. Ampliá presupuesto, zona o ambientes.</div>}
      </div></section>

      <section className="section darksection"><div className="container">
        <div className="decision-grid">
          <div><div className="eyebrow">Tu capacidad de compra</div><h2>Menos ruido. Más contexto para decidir.</h2>
            <p>Con USD {Number(budget).toLocaleString('en-US')} de presupuesto, Propomi puede separar inventario compatible y alternativas cuando existen datos suficientes.</p></div>
          <div className="metrics">
            <div><b>{filtered.length}</b><span>compatibles</span></div>
            <div><b>{filtered.filter(x=>x.zone===zone).length}</b><span>en tu zona</span></div>
            <div><b>{filtered.filter(x=>x.price<Number(budget)).length}</b><span>por debajo del presupuesto</span></div>
            <div><b>{saved.length}</b><span>guardadas</span></div>
          </div>
        </div>
      </div></section>

      <section className="section" id="intencion"><div className="container">
        <div className="sectionhead"><div>
          <div className="eyebrow">Fase 2 · Intent</div><h2>Cada acción demuestra un nivel diferente de intención.</h2>
          <p className="muted">El score es configurable y no reemplaza evidencia real. Se usa para ordenar oportunidades, no para inventar probabilidades.</p>
        </div></div>
        <div className="intentline">{LEVELS.map(([name,n,label])=>
          <div key={String(name)} className="intentstep"><div className="intentnum">{n}</div><b>{String(name)}</b><span>{String(label)}</span></div>)}
        </div>
        <div className="howgrid">
          <div className="howcard"><h3>Tu perfil de intención</h3>
            <div className="profile">
              <div><span>Propiedad</span><b>La que estés evaluando</b></div>
              <div><span>Presupuesto</span><b>USD {Number(budget).toLocaleString('en-US')}</b></div>
              <div><span>Capital disponible</span><b>USD 80.000</b></div>
              <div><span>Financiación</span><b>Sí / a definir</b></div>
              <div><span>Plazo</span><b>30–60 días</b></div>
              <div><span>Datos personales</span><b>OCULTOS</b></div>
            </div>
          </div>
          <div className="howcard"><h3>El comprador mantiene el control</h3>
            <div className="steps">{[['Guardar','Señal de interés'],['Comparar','Evaluación'],['Consultar','Contexto'],['Visitar','Intención'],['Ofertar','Decisión'],['Negociar','Avance comercial']].map(([a,b],i)=>
              <div className="step" key={a}><div className="num">{i+1}</div><div><strong>{a}</strong><span>{b}</span></div></div>)}
            </div>
          </div>
        </div>
      </div></section>

      <section className="section alt" id="como-funciona"><div className="container">
        <div className="sectionhead"><div><div className="eyebrow">Fases 3 + 4</div><h2>De la intención a la negociación.</h2></div></div>
        <div className="flowcards">
          <div className="flowcard"><BarChart3/><span>03 · AGENCIAS</span><h3>Oportunidades activas</h3>
            <p>La agencia ve contexto comercial: presupuesto, timing, intención y propiedad. No ve datos personales automáticamente.</p>
            <ul><li>Solicitar contacto</li><li>Aceptar o proponer visita</li><li>Sugerir otra propiedad</li><li>Ver oportunidades por estado</li></ul></div>
          <div className="flowcard"><Handshake/><span>04 · NEGOCIACIÓN</span><h3>Oferta → contraoferta → avance</h3>
            <p>La negociación queda estructurada y auditada, en lugar de perderse en mensajes aislados.</p>
            <ul><li>Proponer precio</li><li>Aceptar / rechazar</li><li>Contraofertar</li><li>Iniciar negociación</li></ul></div>
          <div className="flowcard"><Sparkles/><span>05 · INTELLIGENCE</span><h3>Aprender del mercado real</h3>
            <p>Los eventos acumulados alimentan comparables, recomendaciones, demanda y pricing intelligence.</p>
            <ul><li>Embudo de intención</li><li>Calidad de oportunidades</li><li>Demanda por zona</li><li>Insights de pricing</li></ul></div>
        </div>
      </div></section>

      <section className="section" id="agentes"><div className="container">
        <div className="sectionhead">
          <div><div className="eyebrow">Vista de agencia · Fase 3</div><h2>No recibas “¿sigue disponible?”. Recibí oportunidades.</h2>
            <p className="muted">Presupuesto, timing e intención de cada comprador — nunca sus datos personales, hasta que decidís revelar el contacto.</p></div>
          <Link href="/agencia" className="primary">Entrar como agencia</Link>
        </div>
        <div className="flowcards">
          <div className="flowcard"><MessageSquare/><span>OFERTAS</span><h3>Recibí propuestas reales</h3>
            <p>Cada oferta llega con monto, capital, forma de pago y plazo — cargados por botones, sin margen para datos de contacto colados en el medio.</p></div>
          <div className="flowcard"><Lock/><span>REVELADO</span><h3>Vos decidís cuándo pagar por el lead</h3>
            <p>El contacto del comprador se revela por cuota de suscripción o pago por lead — nunca antes.</p></div>
          <div className="flowcard"><BarChart3/><span>CUENTA</span><h3>Publicaciones vinculadas por teléfono</h3>
            <p>Iniciá sesión con tu celular y vinculá automáticamente las propiedades que ya te pertenecen.</p></div>
        </div>
      </div></section>

      <section className="section darksection" id="analytics"><div className="container">
        <div className="eyebrow">Fase 5 · Intelligence</div>
        <h2>El activo estratégico no es la cantidad de propiedades.</h2>
        <p>Es la cantidad y calidad de intenciones reales generadas sobre ellas.</p>
        <div className="funnel">{FUNNEL.map((x,i)=><div key={x} style={{'--i':i} as any}><b>{x}</b><span>{Math.max(1,100-i*11)}%</span></div>)}</div>
      </div></section>
    </main>

    {compared.length>0&&<div className="comparebar">
      <span><GitCompare size={16}/> {compared.length} para comparar</span>
      <button onClick={()=>document.getElementById('propiedades')?.scrollIntoView({behavior:'smooth'})}>Ver comparador</button>
      <button onClick={()=>setCompared([])}>Limpiar</button>
    </div>}
    {compared.length>0&&<ComparePanel items={compareItems} onClose={()=>setCompared([])}/>}

    {wizard&&<IntentWizard p={wizard.p} mode={wizard.mode} onClose={()=>setWizard(null)} onDone={m=>{setWizard(null);setToast(m);refreshOffers()}}/>}

    {detail&&<div className="modalback"><div className="modal wide">
      <div className="modalhead">
        <div><span className="eyebrow">Detalle · {detail.freshness}</span><h2>{detail.title}</h2><p className="muted">{detail.zone}, {detail.city} · {detail.source}</p></div>
        <button className="close" onClick={()=>setDetail(null)}>×</button>
      </div>
      <div className="detail">
        {(() => {
          const photos=(detail.images&&detail.images.length>0)?detail.images:(detail.image?[detail.image]:[]);
          const current=photos[Math.min(photoIdx,Math.max(photos.length-1,0))]||detail.image;
          return (
            <div>
              <img src={current} alt={detail.title}/>
              {photos.length>1 && (
                <div style={{display:'flex',gap:8,marginTop:10,flexWrap:'wrap',alignItems:'center'}}>
                  {photos.map((src,i)=>(
                    <button
                      key={src+i}
                      type="button"
                      onClick={()=>setPhotoIdx(i)}
                      style={{
                        padding:0,border:i===photoIdx?'2px solid #c2632f':'2px solid transparent',
                        borderRadius:8,overflow:'hidden',width:56,height:56,cursor:'pointer',background:'#f0ebe6',
                      }}
                    >
                      <img src={src} alt="" style={{width:'100%',height:'100%',objectFit:'cover',display:'block'}}/>
                    </button>
                  ))}
                  <span className="muted small">{photoIdx+1}/{photos.length}</span>
                </div>
              )}
            </div>
          );
        })()}
        <div><div className="bigprice">
            {detail.priceMin!=null&&detail.priceMax!=null&&detail.priceMin!==detail.priceMax
              ? <>USD {detail.priceMin.toLocaleString('en-US')} – {detail.priceMax.toLocaleString('en-US')}</>
              : <>USD {detail.price.toLocaleString('en-US')}</>}
          </div>
          {detail.groupMemberCount!=null&&detail.groupMemberCount>1&&(
            <p className="muted small">Ficha multi-agente · {detail.groupMemberCount} publicaciones</p>
          )}
          <p>{detail.description}</p>
          <div className="specs large">{detail.surface} m² · {detail.rooms} ambientes · {detail.bedrooms} dormitorios · {detail.bathrooms} baño</div>
          <div className="tags"><span>Fuente: {detail.source}</span><span>{detail.freshness}</span></div>
          <div className="detailactions">
            <button className="secondary" onClick={()=>{setDetail(null);setWizard({p:detail,mode:'question'})}}><MessageSquare size={15}/> Hacer pregunta</button>
            <button className="secondary" onClick={()=>{setDetail(null);setWizard({p:detail,mode:'visit'})}}><CalendarDays size={15}/> Pedir visita</button>
            <button className="primary" onClick={()=>{setDetail(null);setWizard({p:detail,mode:'offer'})}}>Proponer precio</button>
          </div>
          <div className="notice"><b>Privacidad:</b> ninguna de estas acciones comparte automáticamente tu teléfono o email.</div>
        </div>
      </div>
    </div></div>}

    {toast&&<div className="toast"><Check size={17}/>{toast}</div>}
    <footer className="footer"><div className="container">
      <div className="brand">prop<span className="omiWord">omi</span></div>
      <p>Propomi.lat · Descubrimiento, intención, decisión y negociación inmobiliaria.</p>
      <small>Arquitectura preparada para LATAM: moneda, país, zona, fuente y unidades desacopladas.</small>
    </div></footer>
  </>;
}
