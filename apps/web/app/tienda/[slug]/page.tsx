'use client';
import {use,useEffect,useState} from 'react';
import Link from 'next/link';
import {ShieldCheck} from 'lucide-react';
import PropertyCard from '../../../components/PropertyCard';
import OfferModal from '../../../components/OfferModal';
import BuyerIdentityModal from '../../../components/BuyerIdentityModal';
import {getAgencyBySlug,getProperties,trackEvent,getBuyerProfile,captureOfferOriginFromUrl} from '../../../lib/api';
import {Agency,BuyerProfile,Property} from '../../../lib/types';

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
  const [offer,setOffer] = useState<Property | null>(null);
  const [detail,setDetail] = useState<Property | null>(null);
  const [photoIdx,setPhotoIdx] = useState(0);
  const [toast,setToast] = useState('');
  const [pendingAction,setPendingAction] = useState<null | (() => void)>(null);

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

  function withIdentity(action: () => void) {
    if (getBuyerProfile()) { action(); return; }
    setPendingAction(() => action);
  }
  function onIdentityDone(_: BuyerProfile) { const a = pendingAction; setPendingAction(null); if (a) a(); }
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
        <p>{items.length} propiedad{items.length === 1 ? '' : 'es'} publicada{items.length === 1 ? '' : 's'} en Propomi.</p>
      </div></section>

      <section className="section"><div className="container">
        <div className="grid">{items.map(p =>
          <PropertyCard key={p.id} p={p} saved={saved.includes(p.id)} compared={false}
            onSave={() => toggleSave(p)} onCompare={() => {}}
            onOffer={() => withIdentity(() => setOffer(p))} onView={() => openDetail(p)}/>)}
        </div>
        {agency && items.length === 0 && <div className="empty">Esta agencia todavía no tiene propiedades activas en Propomi.</div>}
      </div></section>
    </main>

    {offer && <OfferModal p={offer} onClose={() => setOffer(null)} onDone={m => { setOffer(null); setToast(m); }}/>}

    {detail && <div className="modalback"><div className="modal wide">
      <div className="modalhead">
        <div><span className="eyebrow">Detalle · {detail.freshness}</span><h2>{detail.title}</h2><p className="muted">{detail.zone}, {detail.city}</p></div>
        <button className="close" onClick={() => setDetail(null)}>×</button>
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
                    <button key={src+i} type="button" onClick={()=>setPhotoIdx(i)}
                      style={{padding:0,border:i===photoIdx?'2px solid #c2632f':'2px solid transparent',borderRadius:8,overflow:'hidden',width:56,height:56,cursor:'pointer',background:'#f0ebe6'}}>
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
          <div className="detailactions">
            <button className="primary" onClick={() => { setDetail(null); withIdentity(() => setOffer(detail)); }}>Proponer precio</button>
          </div>
          <div className="notice"><b>Privacidad:</b> proponer un precio no comparte automáticamente tu teléfono o email.</div>
        </div>
      </div>
    </div></div>}

    {pendingAction && <BuyerIdentityModal onClose={() => setPendingAction(null)} onDone={onIdentityDone}/>}
    {toast && <div className="toast">{toast}</div>}
  </>;
}
