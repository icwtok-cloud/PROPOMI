'use client';
import {useState} from 'react';
import {Heart,GitCompare,ArrowUpRight,ChevronLeft,ChevronRight} from 'lucide-react';
import {Property} from '../lib/types';

export default function PropertyCard({
  p,saved,compared,onSave,onCompare,onView,onOffer,
}:{
  p:Property;saved:boolean;compared:boolean;
  onSave:()=>void;onCompare:()=>void;onView:()=>void;onOffer:()=>void;
}){
  const photos = (p.images && p.images.length > 0)
    ? p.images
    : (p.image ? [p.image] : []);
  const [idx, setIdx] = useState(0);
  const cover = photos[idx] || photos[0];

  function prev(e: {stopPropagation:()=>void}){
    e.stopPropagation();
    if (photos.length < 2) return;
    setIdx(i => (i - 1 + photos.length) % photos.length);
  }
  function next(e: {stopPropagation:()=>void}){
    e.stopPropagation();
    if (photos.length < 2) return;
    setIdx(i => (i + 1) % photos.length);
  }

  return (
    <article className="property property-card-v2">
      <div className="pcard-media">
        <button type="button" className="imagebtn" onClick={onView} aria-label={`Ver ${p.title}`}>
          {cover
            ? <img src={cover} alt={p.title}/>
            : <div className="pcard-noimg" aria-hidden/>}
          {p.freshness && <span className="fresh">{p.freshness}</span>}
          {p.groupMemberCount != null && p.groupMemberCount > 1 && (
            <span className="fresh multi-badge">Multi-agente · {p.groupMemberCount}</span>
          )}
        </button>
        <button
          type="button"
          className={saved ? 'pcard-heart saved' : 'pcard-heart'}
          onClick={(e)=>{e.stopPropagation();onSave()}}
          aria-label={saved?'Quitar de guardados':'Guardar'}
        >
          <Heart size={18} fill={saved?'currentColor':'none'}/>
        </button>
        {photos.length > 1 && (
          <>
            <button type="button" className="pcard-nav prev" onClick={prev} aria-label="Foto anterior">
              <ChevronLeft size={16}/>
            </button>
            <button type="button" className="pcard-nav next" onClick={next} aria-label="Foto siguiente">
              <ChevronRight size={16}/>
            </button>
            <div className="pcard-dots" aria-hidden>
              {photos.slice(0, 5).map((_, i) => (
                <span key={i} className={i === idx ? 'dot on' : 'dot'}/>
              ))}
            </div>
          </>
        )}
      </div>
      <div className="pbody">
        <div className="prow">
          <span className="muted">{p.type} · {p.zone}{p.city ? `, ${p.city}` : ''}</span>
        </div>
        <h3>{p.title}</h3>
        <strong className="price">
          {p.priceMin != null && p.priceMax != null && p.priceMin !== p.priceMax
            ? <>USD {p.priceMin.toLocaleString('en-US')} – {p.priceMax.toLocaleString('en-US')}</>
            : <>USD {p.price.toLocaleString('en-US')}</>}
        </strong>
        {p.groupMemberCount != null && p.groupMemberCount > 1 && (
          <div className="muted small">Misma propiedad publicada por {p.groupMemberCount} agentes · precio en rango</div>
        )}
        <div className="specs">
          {p.surface != null && <>{p.surface} m² · </>}
          {p.rooms != null && <>{p.rooms} amb.</>}
          {p.bedrooms != null && <> · {p.bedrooms} dorm.</>}
          {p.bathrooms != null && <> · {p.bathrooms} baño</>}
        </div>
        {p.originPublishedAt && <div className="muted small">{p.originPublishedAt}</div>}
        <div className="tags">
          {p.parking && <span>Cochera</span>}
          {p.balcony && <span>Balcón</span>}
          {p.credit && <span>Crédito</span>}
          {p.pool && <span>Pileta</span>}
          {p.petFriendly && <span>Acepta mascotas</span>}
        </div>
        <div className="actions">
          <button type="button" onClick={onCompare} className={compared ? 'secondary active' : 'secondary'}>
            <GitCompare size={15}/>{compared ? 'Comparada' : 'Comparar'}
          </button>
          <button type="button" onClick={onView} className="secondary">Ver detalle <ArrowUpRight size={15}/></button>
          <button type="button" onClick={onOffer} className="primary">Proponer precio</button>
        </div>
      </div>
    </article>
  );
}
