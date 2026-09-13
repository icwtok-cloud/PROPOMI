'use client';import {Heart,GitCompare,ArrowUpRight} from 'lucide-react';import {Property} from '../lib/types';
export default function PropertyCard({p,saved,compared,onSave,onCompare,onView,onOffer}:{p:Property;saved:boolean;compared:boolean;onSave:()=>void;onCompare:()=>void;onView:()=>void;onOffer:()=>void}){
  // Etapa 005: el backend devuelve `images` (hasta 5 fotos, doc 06.1) desde
  // hace varias etapas, pero esta card seguía mostrando solo `image`
  // (singular, DEPRECATED en el modelo). Fallback a `image` para no romper
  // filas viejas que todavía no migraron.
  const cover=p.images&&p.images.length>0?p.images[0]:p.image;
  return <article className="property"><button className="imagebtn" onClick={onView}><img src={cover} alt={p.title}/><span className="fresh">{p.freshness}</span>{p.images&&p.images.length>1&&<span className="fresh" style={{right:8,left:'auto'}}>+{p.images.length-1} fotos</span>}</button><div className="pbody"><div className="prow"><span className="muted">{p.type} · {p.zone}</span><button className="icon" onClick={onSave} aria-label="Guardar"><Heart size={18} fill={saved?'currentColor':'none'}/></button></div><h3>{p.title}</h3><strong className="price">
        {p.priceMin!=null&&p.priceMax!=null&&p.priceMin!==p.priceMax
          ? <>USD {p.priceMin.toLocaleString('en-US')} – {p.priceMax.toLocaleString('en-US')}</>
          : <>USD {p.price.toLocaleString('en-US')}</>}
      </strong>
      {p.groupMemberCount&&p.groupMemberCount>1&&(
        <div className="muted small">{p.groupMemberCount} publicaciones de distintos agentes · una sola ficha</div>
      )}<div className="specs">{p.surface} m² · {p.rooms} amb. · {p.bedrooms} dorm. · {p.bathrooms} baño</div>{p.originPublishedAt&&<div className="muted small">{p.originPublishedAt}</div>}<p>{p.description}</p><div className="tags">{p.parking&&<span>Cochera</span>}{p.balcony&&<span>Balcón</span>}{p.credit&&<span>Crédito</span>}{p.pool&&<span>Pileta</span>}{p.petFriendly&&<span>Acepta mascotas</span>}</div><div className="actions"><button onClick={onCompare} className={compared?'secondary active':'secondary'}><GitCompare size={15}/>{compared?'Comparada':'Comparar'}</button><button onClick={onView} className="secondary">Ver detalle <ArrowUpRight size={15}/></button><button onClick={onOffer} className="primary">Proponer precio</button></div></div></article>
}
