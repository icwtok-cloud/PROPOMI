'use client';
import {use,useEffect,useState} from 'react';
import Link from 'next/link';
import {CalendarDays,ChevronLeft,ChevronRight,MessageSquare,ShieldCheck} from 'lucide-react';
import PropertyCard from '../../../components/PropertyCard';
import IntentWizard, {WizardMode} from '../../../components/IntentWizard';
import {getAgencyBySlug,getProperties,trackEvent,captureOfferOriginFromUrl} from '../../../lib/api';
import {Agency,Property} from '../../../lib/types';

// Etapa 015 (subdominios por agencia): storefront público mínimo de UNA
// agencia. Llega acá vía:
//   a) `{slug}.propomi.lat` -> middleware.ts reescribe '/' a '/tienda/[slug]'
//      (URL visible sigue siendo el subdominio, el rewrite es interno).
//   b) directo a `/tienda/[slug]` en el dominio raíz, útil para probar sin
//      DNS wildcard configurado todavía.
// A propósito NO reusa toda la home (búsqueda multi-zona, comparador,
// secciones de producto) — es solo "estas son las propiedades de ESTA
// agencia", con la misma card y el mismo flujo de oferta que ya existen.
export default function AgencyStorefront({params}: {params: Promise<{slug: string}>}) {
  const {slug} = use(params);
  const [agency,setAgency] = useState<Agency | null>(null);
  const [notFound,setNotFound] = useState(false);
  const [items,setItems] = useState<Property[]>([]);
  const [saved,setSaved] = useState<string[]>([]);
  const [wizard,setWizard] = useState<{p:Property;mode:WizardMode}|null>(null);
  const [detail,setDetail] = useState<Property | null>(null);
  const [photoIdx,setPhotoIdx] = useState(0);
  const [toast,setToast] = useState('');

  useEffect(() => {
    // T9.3: el storefront marca origen = slug de la agencia (o ?o= si viene).
    try {
      const q = new URLSearchParams(window.location.search);
      if (!(q.get('o') || q.get('origin'))) {
        sessionStorage.setItem('propomi-offer-origin', slug.toLowerCase().replace(/[^a-z0-9_-]/g,'').slice(0,80));
      } else {
        captureOfferOriginFromUrl();
      }
    } catch {}
  }, [slug]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const a = await getAgencyBySlug(slug);
        if (cancelled) return;
        setAgency(a);
        const props = await getProperties({agency_id: a.id});
        if (!cancelled) setItems(props);
      } catch (err: any) {
        if (!cancelled && err?.status === 404) setNotFound(true);
      }
    })();
    return () => { cancelled = true; };
  }, [slug]);

  useEffect(() => { if (toast) { const t = setTimeout(() => setToast(''), 3500); return () => clearTimeout(t); } }, [toast]);

  function toggleSave(p: Property) {
    const next = saved.includes(p.id) ? saved.filter(x => x !== p.id) : [...saved, p.id];
    setSaved(next);
    trackEvent('property_save', p.id);
  }
  function openDetail(p: Property) { setDetail(p);setPhotoIdx(0); trackEvent('property_view', p.id); }

  if (notFound) {
    return <div className="container" style={{padding: '80px 0', textAlign: 'center'}}>
      <h1>Agencia no encontrada</h1>
      <p className="muted">El link que seguiste no corresponde a ninguna agencia activa en Propomi.</p>
      <Link href="/" className="primary" style={{display: 'inline-flex', marginTop: 16}}>Ir a Propomi</Link>
    </div>;
  }

  return <>
    <nav className="nav"><div className="container navin">
      <Link href="/" className="brand">prop<span className="omiWord">omi</span></Link>
      <div className="navlinks">{agency && <span className="muted">{agency.city}</span>}</div>
      <Link href="/" className="primary" style={{height: 38, padding: '0 16px'}}>Ver todo Propomi</Link>
    </div></nav>

    <main>
      <section className="hero"><div className="container">
        <div className="eyebrow">Storefront de agencia</div>
        <h1>{agency ? agency.name : 'Cargando…'}</h1>
        {agency && <div className="focus-badge"><ShieldCheck size={14}/> {agency.verificationStatus === 'VERIFIED' ? 'Agencia verificada' : 'Verificación pendiente'}</div>}
        <p className="storefront-hero-sub">{items.length} propiedad{items.length === 1 ? '' : 'es'} publicada{items.length === 1 ? '' : 's'} en Propomi. Explorá, preguntá o proponé precio con el mismo flujo seguro que en el portal.</p>
      </div></section>

      <section className="section"><div className="container">
        <div className="grid">{items.map(p =>
          <PropertyCard key={p.id} p={p} saved={saved.includes(p.id)} compared={false}
            onSave={() => toggleSave(p)} onCompare={() => {}}
            onOffer={() => setWizard({p, mode:'offer'})} onView={() => openDetail(p)}/>)}
        </div>
        {agency && items.length === 0 && <div className="empty">Esta agencia todavía no tiene propiedades activas en Propomi.</div>}
      </div></section>
    </main>

    {wizard && <IntentWizard p={wizard.p} mode={wizard.mode} onClose={() => setWizard(null)} onDone={m => { setWizard(null); setToast(m); }}/>}

    {detail && <div className="modalback"><div className="modal wide">
      <div className="modalhead">
        <div>
          <span className="eyebrow">Detalle · {detail.freshness || 'publicación'}</span>
          <h2>{detail.title}</h2>
          <p className="muted">{detail.zone}, {detail.city}{detail.source ? ` · ${detail.source}` : ''}</p>
        </div>
        <button className="close" type="button" onClick={() => setDetail(null)} aria-label="Cerrar">×</button>
      </div>
      <div className="detail">
        {(() => {
          const photos=(detail.images&&detail.images.length>0)?detail.images:(detail.image?[detail.image]:[]);
          const current=photos[Math.min(photoIdx,Math.max(photos.length-1,0))]||detail.image;
          return (
            <div>
              {current ? (
                <div className="detail-photo-wrap">
                  <img src={current} alt={detail.title}/>
                  {photos.length>1 && (
                    <>
                      <button type="button" className="detail-photo-nav prev" aria-label="Foto anterior" onClick={()=>setPhotoIdx(i=>(i-1+photos.length)%photos.length)}><ChevronLeft size={18}/></button>
                      <button type="button" className="detail-photo-nav next" aria-label="Foto siguiente" onClick={()=>setPhotoIdx(i=>(i+1)%photos.length)}><ChevronRight size={18}/></button>
                    </>
                  )}
                </div>
              ) : (
                <div className="detail-photo-placeholder">Sin foto disponible</div>
              )}
              {photos.length>1 && (
                <div className="detail-thumbs">
                  {photos.map((src,i)=>(
                    <button key={src+i} type="button" className={i===photoIdx?'detail-thumb active':'detail-thumb'} onClick={()=>setPhotoIdx(i)}>
                      <img src={src} alt=""/>
                    </button>
                  ))}
                  <span className="muted small">{photoIdx+1}/{photos.length}</span>
                </div>
              )}
            </div>
          );
        })()}
        <div>
          <div className="bigprice">
            {detail.priceMin!=null&&detail.priceMax!=null&&detail.priceMin!==detail.priceMax
              ? <>USD {detail.priceMin.toLocaleString('en-US')} – {detail.priceMax.toLocaleString('en-US')}</>
              : <>USD {Number(detail.price||0).toLocaleString('en-US')}</>}
          </div>
          {detail.groupMemberCount!=null&&detail.groupMemberCount>1&&(
            <p className="muted small">Ficha multi-agente · {detail.groupMemberCount} publicaciones</p>
          )}
          <p>{detail.description}</p>
          <div className="specs large">{detail.surface} m² · {detail.rooms} ambientes · {detail.bedrooms} dormitorios · {detail.bathrooms} baño</div>
          {(detail.source || detail.freshness) && (
            <div className="tags">
              {detail.source && <span>Fuente: {detail.source}</span>}
              {detail.freshness && <span>{detail.freshness}</span>}
            </div>
          )}
          <div className="detailactions">
            <button type="button" className="secondary" onClick={() => { setDetail(null); setWizard({p: detail, mode: 'question'}); }}>
              <MessageSquare size={15}/> Hacer pregunta
            </button>
            <button type="button" className="secondary" onClick={() => { setDetail(null); setWizard({p: detail, mode: 'visit'}); }}>
              <CalendarDays size={15}/> Pedir visita
            </button>
            <button type="button" className="primary" onClick={() => { setDetail(null); setWizard({p: detail, mode: 'offer'}); }}>
              Proponer precio
            </button>
          </div>
          <div className="notice"><b>Privacidad:</b> ninguna de estas acciones comparte automáticamente tu teléfono o email.</div>
        </div>
      </div>
    </div></div>}

    {toast && <div className="toast">{toast}</div>}
  </>;
}
