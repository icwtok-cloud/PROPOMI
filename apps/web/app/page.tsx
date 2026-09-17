'use client';
import {useEffect,useMemo,useState} from 'react';
import Link from 'next/link';
import {Search,Check,GitCompare,ShieldCheck,Sparkles,CalendarDays,Handshake,BarChart3,MessageSquare,Lock,ChevronDown,ChevronLeft,ChevronRight,X,Building2,Home as HomeIcon,Store,Map,Briefcase} from 'lucide-react';
import PropertyCard from '../components/PropertyCard';
import IntentWizard, {WizardMode} from '../components/IntentWizard';
import ComparePanel from '../components/ComparePanel';
import {getProperties,getPropertiesDeduped,trackEvent,listOffers,isOffersRestricted,getOrCreateBuyerSession,captureOfferOriginFromUrl,trackSearchPerformed,getPropertyFilters,getMySuggestions,engageSuggestion} from '../lib/api';
import {Property,Offer} from '../lib/types';
import {canonicalAdminUnits,adminUnitLabel,propertyTypeLabel} from '../lib/geo';

const LEVELS=[['Ver',1,'Exploración'],['Guardar',2,'Interés'],['Comparar',3,'Evaluación'],['Preguntar',4,'Consulta'],['Visitar',6,'Intención'],['Ofertar',8,'Decisión'],['Negociar',10,'Negociación'],['Compartir contacto',10,'Contacto']];
const FUNNEL=['Vistas','Guardados','Comparaciones','Consultas','Visitas','Ofertas','Negociaciones','Contacto compartido','Operaciones'];
const PROPERTY_TYPES=['Todos','Departamento','Casa','PH','Oficina','Local','Terreno','En Pozo'];

/** Heurística espejo del backend (GET /properties/filters): ciudad válida si
 *  tiene letras, >2 chars, no es solo dígitos, y no parece dirección. */
function isValidCityName(name: string | null | undefined): boolean {
  const s = (name || '').trim();
  if (s.length <= 2) return false;
  if (!/[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/.test(s)) return false;
  if (/^\d+$/.test(s)) return false;
  if (/^(av\.?|avenida|calle|ruta|pasaje|pje\.?)\b/i.test(s)) return false;
  if (/\d{3,5}\s*$/.test(s) && /\s/.test(s)) return false;
  return true;
}

const COUNTRY_OPTIONS=['Todos','Argentina','Paraguay','Uruguay'];

export default function Home(){
  const [items,setItems]=useState<Property[]>([]);
  const [budget,setBudget]=useState('');
  // Etapa 2 (bug reportado 2026-09-15): "Dónde" ya no es una lista fija de
  // barrios de Buenos Aires — city/zone se autodetectan de lo que el
  // crawler+carga manual efectivamente tienen en la base (GET
  // /properties/filters), para que cualquier fuente nueva (ej. CordobaProp)
  // aparezca sola en el buscador sin tocar este archivo.
  const [cities,setCities]=useState<string[]>([]);
  const [zonesByCity,setZonesByCity]=useState<Record<string,string[]>>({});
  const [country,setCountry]=useState('Todos');
  const [province,setProvince]=useState('');
  const [provincesByCountry,setProvincesByCountry]=useState<Record<string,string[]>>({});
  const [citiesByProvince,setCitiesByProvince]=useState<Record<string,string[]>>({});
  const [city,setCity]=useState('');
  const [zone,setZone]=useState('');
  const [investmentOnly,setInvestmentOnly]=useState(false);
  const [ptype,setPtype]=useState('Todos');
  const [rooms,setRooms]=useState('Todos');
  const [parking,setParking]=useState(false);
  const [credit,setCredit]=useState(false);
  const [saved,setSaved]=useState<string[]>([]);
  const [compared,setCompared]=useState<string[]>([]);
  const [wizard,setWizard]=useState<{p:Property;mode:WizardMode}|null>(null);
  const [detail,setDetail]=useState<Property|null>(null);
  const [buyerSuggestions,setBuyerSuggestions]=useState<Array<{id:string;property:Property;suggested_by_agency_name:string|null;source_property_id:string;status:string}>>([]);
  useEffect(()=>{
    getMySuggestions().then(r=>setBuyerSuggestions(r.suggestions||[])).catch(()=>setBuyerSuggestions([]));
  },[]);
  const [photoIdx,setPhotoIdx]=useState(0);
  const [offers,setOffers]=useState<Offer[]>([]);
  const [toast,setToast]=useState('');
  const [loadError,setLoadError]=useState<string|null>(null);
  const [isLoading,setIsLoading]=useState(true);
  const [balcony,setBalcony]=useState(false);
  const [sortBy,setSortBy]=useState<'relevance'|'price_asc'|'price_desc'|'recent'>('relevance');
  const [openSeg,setOpenSeg]=useState<'where'|'type'|'budget'|null>('where');
  const [moreFilters,setMoreFilters]=useState(false);
  const [searchSticky,setSearchSticky]=useState(false);

  useEffect(()=>{captureOfferOriginFromUrl()},[]);
  useEffect(()=>{(async()=>{
    try{
      const f=await getPropertyFilters();
      setCities(f.cities);
      setZonesByCity(f.zonesByCity||{});
      if((f as any).provincesByCountry) setProvincesByCountry((f as any).provincesByCountry);
      if((f as any).citiesByProvince) setCitiesByProvince((f as any).citiesByProvince);
      // Sin ciudad por defecto: el listado arranca mostrando todo el catálogo.
      // El usuario elige país/provincia/ciudad/zona desde el pill.
    }catch(e:any){console.warn('filters',e?.message||e)}
  })()},[]);
  useEffect(()=>{
    // Sin ciudad elegida no forzar zona (evita "El Mirador" de fábrica).
    if(!city){
      if(zone) setZone('');
      return;
    }
    const zonesForCity=zonesByCity[city]||[];
    if(!zone||!zonesForCity.includes(zone)){
      setZone(zonesForCity[0]||'');
    }
  },[city,zonesByCity]);
  useEffect(()=>{(async()=>{
    try{
      setIsLoading(true);
      setLoadError(null);
      const items=await getPropertiesDeduped();
      setItems(items);
      try{
        const s=await getOrCreateBuyerSession();
        const offersList=await listOffers(s);
        setOffers(isOffersRestricted(offersList)?[]:(Array.isArray(offersList)?offersList:[]));
      }catch(e:any){console.warn('offers',e?.message||e)}
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
    }catch(e:any){
      setLoadError(e?.message||'No pudimos cargar las propiedades. Probá recargar.');
      setItems([]);
    }finally{
      setIsLoading(false);
    }
  })()},[]);
  useEffect(()=>{if(toast){const t=setTimeout(()=>setToast(''),3500);return()=>clearTimeout(t)}},[toast]);
  useEffect(()=>{
    const onScroll=()=>{
      const s=window.scrollY>320;
      setSearchSticky(s);
    };
    window.addEventListener('scroll',onScroll,{passive:true});
    return ()=>window.removeEventListener('scroll',onScroll);
  },[]);
  // Cerrar popover al click fuera
  useEffect(()=>{
    if(!openSeg)return;
    const close=(e:MouseEvent)=>{
      const el=document.getElementById('search-pill');
      if(el&&!el.contains(e.target as Node))setOpenSeg(null);
    };
    document.addEventListener('mousedown',close);
    return ()=>document.removeEventListener('mousedown',close);
  },[openSeg]);


  const filtered=useMemo(()=>{
    let list=items.filter(p=>{
      const pCountry=(p.country||'Argentina');
      const pProvince=(p.province||'');
      if(country&&country!=='Todos'&&pCountry!==country) return false;
      if(province&&pProvince!==province) return false;
      if(city){
        if(city==='Sin descripción'){
          if(isValidCityName(p.city)) return false;
        }else if(p.city!==city) return false;
      }
      if(zone&&p.zone!==zone) return false;
      if(ptype==='En Pozo'){ if(!p.underConstruction) return false; }
      else if(ptype!=='Todos'&&p.type!==ptype) return false;
      if(rooms&&rooms!=='Todos'&&p.rooms!==Number(rooms)) return false;
      if(!(p.price<=Number(budget||Infinity))) return false;
      if(parking&&!p.parking) return false;
      if(credit&&!p.credit) return false;
      if(balcony&&!p.balcony) return false;
      if(investmentOnly&&!p.investmentOpportunity) return false;
      return true;
    });
    if(sortBy==='price_asc')list=[...list].sort((a,b)=>a.price-b.price);
    else if(sortBy==='price_desc')list=[...list].sort((a,b)=>b.price-a.price);
    else if(sortBy==='recent')list=[...list].sort((a,b)=>{
      const da=a.originPublishedAt||a.detectedAt||'';
      const db=b.originPublishedAt||b.detectedAt||'';
      return db.localeCompare(da);
    });
    // relevance: keep API/priority order as received
    return list;
  },[items,country,province,city,zone,ptype,rooms,budget,parking,credit,balcony,investmentOnly,sortBy]);

  // Si el default Buenos Aires no tiene inventario fresco, no dejar pantalla vacía.
  useEffect(()=>{
    if(city!=='Buenos Aires'||!items.length) return;
    const anyBA=items.some(p=>p.city==='Buenos Aires');
    if(!anyBA) setCity('');
  },[items,city]);

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


  const whereLabel=[country&&country!=='Todos'?country:null,province||null,city||null,zone||null].filter(Boolean).join(' · ')||'Cualquier lugar';
  const typeLabel=ptype==='Todos'?(rooms==='Todos'?'Tipo y ambientes':`${rooms} amb.`):(rooms==='Todos'?propertyTypeLabel(ptype,country):`${propertyTypeLabel(ptype,country)} · ${rooms} amb.`);
  const budgetLabel=budget?`Hasta USD ${Number(budget).toLocaleString('en-US')}`:'Cualquier presupuesto';
  const typeIcon=(name:string)=>{
    if(name==='Casa')return <HomeIcon size={18}/>;
    if(name==='Oficina')return <Briefcase size={18}/>;
    if(name==='Terreno')return <Map size={18}/>;
    if(name==='Local')return <Store size={18}/>;
    return <Building2 size={18}/>;
  };
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
        <div id="search-pill" className={searchSticky?'search-pill-wrap sticky':'search-pill-wrap'}>
          <div className="search-pill" role="search">
            <button type="button" className={openSeg==='where'?'pill-seg active':'pill-seg'} onClick={()=>setOpenSeg(openSeg==='where'?null:'where')}>
              <span className="pill-label">Dónde</span>
              <span className="pill-value">{whereLabel}</span>
            </button>
            <span className="pill-divider" aria-hidden/>
            <button type="button" className={openSeg==='type'?'pill-seg active':'pill-seg'} onClick={()=>setOpenSeg(openSeg==='type'?null:'type')}>
              <span className="pill-label">Tipo y ambientes</span>
              <span className="pill-value">{typeLabel}</span>
            </button>
            <span className="pill-divider" aria-hidden/>
            <button type="button" className={openSeg==='budget'?'pill-seg active':'pill-seg'} onClick={()=>setOpenSeg(openSeg==='budget'?null:'budget')}>
              <span className="pill-label">Presupuesto</span>
              <span className="pill-value">{budgetLabel}</span>
            </button>
            <span className="pill-icon" aria-hidden><Search size={16}/></span>
          </div>

          {openSeg==='where'&&(
            <div className="pill-popover">
              <div className="pill-pop-head"><strong>¿Dónde buscás?</strong><button type="button" className="icon" onClick={()=>setOpenSeg(null)} aria-label="Cerrar"><X size={18}/></button></div>
              <label>País
                <select value={country} onChange={e=>{setCountry(e.target.value);setProvince('');setCity('');setZone('')}}>
                  {COUNTRY_OPTIONS.map(c=><option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label>{adminUnitLabel(country)}
                <select value={province} onChange={e=>{setProvince(e.target.value);setCity('');setZone('')}}>
                  <option value="">Todas</option>
                  {(
                    country!=='Todos'
                      ? Array.from(new Set([...(canonicalAdminUnits(country)), ...(provincesByCountry[country]||[])])).sort((a,b)=>a.localeCompare(b,'es'))
                      : Array.from(new Set([
                          ...canonicalAdminUnits('Argentina'),
                          ...canonicalAdminUnits('Paraguay'),
                          ...canonicalAdminUnits('Uruguay'),
                          ...Object.values(provincesByCountry).flat(),
                        ])).sort((a,b)=>a.localeCompare(b,'es'))
                  ).map(pr=><option key={pr} value={pr}>{pr}</option>)}
                </select>
              </label>
              <label>Ciudad
                <select value={city} onChange={e=>{setCity(e.target.value);setZone('')}}>
                  <option value="">Todas</option>
                  {(
                    province
                      ? (citiesByProvince[`${country==='Todos'?'Argentina':country}|${province}`]||cities)
                      : cities
                  ).map(c=><option key={c} value={c}>{c}</option>)}
                </select>
              </label>
              <label>Zona
                <select value={zone} onChange={e=>setZone(e.target.value)}>
                  <option value="">Todas</option>
                  {(zonesByCity[city]||[]).map(z=><option key={z} value={z}>{z}</option>)}
                </select>
              </label>
            </div>
          )}
          {openSeg==='type'&&(
            <div className="pill-popover">
              <div className="pill-pop-head"><strong>Tipo de propiedad</strong><button type="button" className="icon" onClick={()=>setOpenSeg(null)} aria-label="Cerrar"><X size={18}/></button></div>
              <div className="type-chip-grid">
                {PROPERTY_TYPES.map(name=>(
                  <button type="button" key={name} className={ptype===name?'type-chip selected':'type-chip'} onClick={()=>setPtype(name)}>
                    {name!=='Todos'&&typeIcon(name)}
                    <span>{propertyTypeLabel(name, country)}</span>
                  </button>
                ))}
              </div>
              <label className="filter-check" style={{display:'flex',alignItems:'center',gap:8,margin:'10px 0 4px',cursor:'pointer',fontWeight:650}}>
                <input type="checkbox" checked={investmentOnly} onChange={e=>setInvestmentOnly(e.target.checked)}/>
                <span>Oportunidad de Inversión</span>
              </label>
              <label style={{marginTop:12}}>Ambientes
                <div className="rooms-row">
                  {['1','2','3','Todos'].map(r=>(
                    <button type="button" key={r} className={rooms===r?'chip active':'chip'} onClick={()=>setRooms(r)}>{r}</button>
                  ))}
                </div>
              </label>
            </div>
          )}
          {openSeg==='budget'&&(
            <div className="pill-popover">
              <div className="pill-pop-head"><strong>Presupuesto máximo</strong><button type="button" className="icon" onClick={()=>setOpenSeg(null)} aria-label="Cerrar"><X size={18}/></button></div>
              <label className="budget-big">USD
                <input value={budget} onChange={e=>setBudget(e.target.value.replace(/[^\d]/g,''))} inputMode="numeric" placeholder="120000"/>
              </label>
              <p className="muted small">Filtrado en vivo · solo propiedades en venta</p>
            </div>
          )}

          {!searchSticky&&<div className="search-meta">
            <div className="filterrow pill-chips">
              <button type="button" className={parking?'chip active':'chip'} onClick={()=>setParking(!parking)}>Cochera</button>
              <button type="button" className={credit?'chip active':'chip'} onClick={()=>setCredit(!credit)}>Apto crédito</button>
              <button type="button" className={balcony?'chip active':'chip'} onClick={()=>setBalcony(!balcony)}>Balcón</button>
              <button type="button" className={moreFilters?'chip active':'chip'} onClick={()=>setMoreFilters(!moreFilters)}>
                Más filtros <ChevronDown size={14}/>
              </button>
            </div>
            <div className="results-live">
              <span className="results-count">{isLoading?'…':`${filtered.length} resultado${filtered.length===1?'':'s'}`}</span>
              <label className="sort-label">Ordenar
                <select value={sortBy} onChange={e=>setSortBy(e.target.value as any)}>
                  <option value="relevance">Relevancia</option>
                  <option value="price_asc">Precio: menor a mayor</option>
                  <option value="price_desc">Precio: mayor a menor</option>
                  <option value="recent">Más recientes</option>
                </select>
              </label>
            </div>
          </div>}
          {!searchSticky&&moreFilters&&(
            <div className="more-filters-panel muted small">
              Zona y ambientes también están en la barra de arriba. Los chips activan filtros booleanos del listado (cochera, crédito, balcón).
            </div>
          )}
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
            <p className="muted">{isLoading?'Cargando…':`${filtered.length} compatibles con tus criterios actuales.`}</p></div>
        </div>
        {isLoading&&(
          <div className="properties-grid skeleton-grid" aria-busy="true" aria-label="Cargando propiedades">
            {[1,2,3,4,5,6].map(i=>(
              <div key={i} className="property skeleton-card">
                <div className="skeleton-img"/>
                <div className="skeleton-line w60"/>
                <div className="skeleton-line w90"/>
                <div className="skeleton-line w40"/>
              </div>
            ))}
          </div>
        )}
        {!isLoading&&(
        <div className="properties-grid">{filtered.map(p=>
          <PropertyCard key={p.id} p={p} saved={saved.includes(p.id)} compared={compared.includes(p.id)}
            onSave={()=>toggleSave(p)} onCompare={()=>toggleCompare(p)}
            onOffer={()=>setWizard({p,mode:'offer'})} onView={()=>openDetail(p)}/>)}
        </div>
        )}
        {!isLoading&&filtered.length===0&&!loadError&&<div className="empty">No encontramos propiedades con estos criterios. Ampliá presupuesto, zona o ambientes.</div>}
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
              <div className="detail-photo-wrap">
                <img src={current} alt={detail.title}/>
                {photos.length>1 && (
                  <>
                    <button type="button" className="detail-photo-nav prev" aria-label="Foto anterior" onClick={()=>setPhotoIdx(i=>(i-1+photos.length)%photos.length)}><ChevronLeft size={18}/></button>
                    <button type="button" className="detail-photo-nav next" aria-label="Foto siguiente" onClick={()=>setPhotoIdx(i=>(i+1)%photos.length)}><ChevronRight size={18}/></button>
                  </>
                )}
              </div>
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
            {buyerSuggestions.filter(s=>s.source_property_id===detail.id).map(s=>(
              <div key={s.id} className="summarycard" style={{marginBottom:12,padding:'14px 16px'}}>
                <div className="eyebrow">Te puede interesar</div>
                <p className="muted small" style={{margin:'6px 0 10px'}}>
                  Te sugerimos esta propiedad de <strong>{s.suggested_by_agency_name||'otra agencia'}</strong> porque puede ajustarse mejor a tu búsqueda.
                </p>
                <div style={{display:'flex',gap:12,alignItems:'center',flexWrap:'wrap'}}>
                  {(s.property.images?.[0]||s.property.image) ? (
                    <img src={s.property.images?.[0]||s.property.image} alt="" style={{width:72,height:72,objectFit:'cover',borderRadius:10}}/>
                  ) : null}
                  <div style={{flex:1,minWidth:140}}>
                    <strong>{s.property.title}</strong>
                    <div className="muted small">{s.property.zone} · USD {Number(s.property.price||0).toLocaleString('en-US')}</div>
                  </div>
                  <button type="button" className="primary" onClick={async()=>{
                    try{await engageSuggestion(s.id)}catch{}
                    setDetail(s.property);
                    setPhotoIdx(0);
                    ev('property_view',s.property.id);
                    getMySuggestions().then(r=>setBuyerSuggestions(r.suggestions||[])).catch(()=>{});
                  }}>Ver propiedad</button>
                </div>
              </div>
            ))}
            <button className="secondary" onClick={()=>{setDetail(null);setWizard({p:detail,mode:'question'})}}><MessageSquare size={15}/> Hacer pregunta</button>
            <button className="secondary" onClick={()=>{setDetail(null);setWizard({p:detail,mode:'visit'})}}><CalendarDays size={15}/> Pedir visita</button>
            <button className="primary" onClick={()=>{setDetail(null);setWizard({p:detail,mode:'offer'})}}>Proponer precio</button>
          </div>
          <div className="notice"><b>Privacidad:</b> ninguna de estas acciones comparte automáticamente tu teléfono o email.</div>
        </div>
      </div>
    </div></div>}

    {loadError&&<div className="notice" role="alert" style={{margin:'12px 0'}}>{loadError}</div>}
    {toast&&<div className="toast"><Check size={17}/>{toast}</div>}
    <footer className="footer"><div className="container">
      <div className="brand">prop<span className="omiWord">omi</span></div>
      <p>Propomi.lat · Descubrimiento, intención, decisión y negociación inmobiliaria.</p>
      <small>Arquitectura preparada para LATAM: moneda, país, zona, fuente y unidades desacopladas.</small>
    </div></footer>
  </>;
}
