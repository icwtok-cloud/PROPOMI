import {Agency,BuyerProfile,DemandRequest,DemandSummary,EventName,Intent,Lead,Offer,Opportunity,PendingAgency,Property,ReviewQueueItem,Role,Session} from './types';
export type {PendingAgency,ReviewQueueItem} from './types';

import {PROPERTIES} from './data';
const base=process.env.NEXT_PUBLIC_API_URL;
async function req<T>(path:string,init?:RequestInit,token?:string):Promise<T>{const r=await fetch(`${base}${path}`,{...init,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...(init?.headers||{})},cache:'no-store'});if(!r.ok){let message=`Error ${r.status}`;let detail:any=undefined;try{const body=await r.json();detail=body?.detail;message=typeof detail==='string'?detail:(detail?.message||JSON.stringify(detail)||message)}catch{try{message=await r.text()||message}catch{}}const err:any=new Error(message);err.status=r.status;err.detail=detail;throw err}return r.json()}

export async function suggestProperty(propertyId: string, suggestedPropertyId: string, session?: Session | null) {
  if (!base) return { id: `demo-suggest-${Date.now()}`, status: 'SENT' };
  return req<{id:string;status:string}>(`/properties/${propertyId}/suggest`, {
    method: 'POST',
    body: JSON.stringify({ suggested_property_id: suggestedPropertyId }),
  }, session?.token);
}

export async function getMySuggestions(session?: Session | null) {
  if (!base) return { suggestions: [] as Array<{id:string;property:Property;suggested_by_agency_name:string|null;source_property_id:string;status:string}> };
  const s = session || await getOrCreateBuyerSession();
  if (!s) throw new Error('Sesión requerida');
  return req<{ suggestions: Array<{ id: string; property: Property; suggested_by_agency_name: string | null; source_property_id: string; status: string }> }>('/buyers/me/suggestions', undefined, s.token);
}

export async function engageSuggestion(suggestionId: string, session?: Session | null) {
  if (!base) return { status: 'ENGAGED' };
  const s = session || await getOrCreateBuyerSession();
  if (!s) throw new Error('Sesión requerida');
  return req<{status:string}>(`/property-suggestions/${suggestionId}/engage`, { method: 'POST' }, s.token);
}

export type PropertiesPage = {items:Property[];total:number;limit:number;offset:number;has_more:boolean};

/** Búsqueda paginada. Default limit=48. Devuelve página + total (no el catálogo entero). */
export async function getProperties(
  filters?: Record<string, string | number | boolean>
): Promise<PropertiesPage> {
  if (!base) {
    const agencyId = filters?.agency_id;
    const all = agencyId ? PROPERTIES.filter(p => p.agencyId === agencyId) : PROPERTIES;
    const limit = Number(filters?.limit ?? 48);
    const offset = Number(filters?.offset ?? 0);
    const items = all.slice(offset, offset + limit);
    return {items, total: all.length, limit, offset, has_more: offset + items.length < all.length};
  }
  const qs = new URLSearchParams();
  const merged = {limit: 48, offset: 0, ...(filters || {})};
  Object.entries(merged).forEach(([k, v]) => {
    if (v !== '' && v !== undefined && v !== null) qs.set(k, String(v));
  });
  const data = await req<PropertiesPage | Property[]>(`/properties?${qs}`);
  // Compat: si el backend aún devolviera array plano
  if (Array.isArray(data)) {
    return {items: data, total: data.length, limit: data.length, offset: 0, has_more: false};
  }
  return data;
}

/** Lista plana (admin / deep-link). Pide páginas hasta agotar o tope de seguridad. */
export async function getPropertiesAll(
  filters?: Record<string, string | number | boolean>,
  maxPages = 20
): Promise<Property[]> {
  const out: Property[] = [];
  let offset = 0;
  const limit = 100;
  for (let i = 0; i < maxPages; i++) {
    const page = await getProperties({...(filters || {}), limit, offset});
    out.push(...page.items);
    if (!page.has_more) break;
    offset += page.items.length;
  }
  return out;
}

export async function getPropertiesRandom(n:number=30,filters?:Record<string,string|number|boolean>):Promise<Property[]>{
  if(!base){
    const agencyId=filters?.agency_id;
    const pool=agencyId?PROPERTIES.filter(p=>p.agencyId===agencyId):PROPERTIES;
    return pool.slice(0,Math.max(0,n));
  }
  const qs=new URLSearchParams();
  qs.set('n',String(n));
  Object.entries(filters||{}).forEach(([k,v])=>v!==''&&v!==undefined&&qs.set(k,String(v)));
  return req<Property[]>(`/properties/random?${qs}`);
}
export async function getProperty(id:string){if(!base)return PROPERTIES.find(p=>p.id===id)!;return req<Property>(`/properties/${id}`)}
export async function getPropertyFilters(){if(!base){const byCity:Record<string,string[]>={};PROPERTIES.forEach(p=>{byCity[p.city]=Array.from(new Set([...(byCity[p.city]||[]),p.zone]))});return {cities:Object.keys(byCity),zonesByCity:byCity}}return req<{cities:string[];zonesByCity:Record<string,string[]>}>('/properties/filters')}
export type GeoCatalog={countries:string[];provincesByCountry:Record<string,string[]>;citiesByProvince:Record<string,string[]>};
export async function getGeoCatalog():Promise<GeoCatalog>{
  if(!base){
    // Fallback offline alineado con lib/geo.ts (provincias; ciudades mínimas)
    return {
      countries:['Argentina','Paraguay','Uruguay'],
      provincesByCountry:{
        Argentina:['Buenos Aires','CABA','Córdoba','Mendoza','Santa Fe'],
        Paraguay:['Asunción','Central','Alto Paraná'],
        Uruguay:['Montevideo','Canelones','Maldonado'],
      },
      citiesByProvince:{
        'Argentina|Buenos Aires':['La Plata','Mar del Plata'],
        'Argentina|CABA':['Ciudad Autónoma de Buenos Aires'],
        'Argentina|Córdoba':['Córdoba'],
        'Argentina|Mendoza':['Mendoza'],
        'Argentina|Santa Fe':['Rosario','Santa Fe'],
        'Paraguay|Asunción':['Asunción'],
        'Paraguay|Central':['San Lorenzo','Luque'],
        'Paraguay|Alto Paraná':['Ciudad del Este'],
        'Uruguay|Montevideo':['Montevideo'],
        'Uruguay|Canelones':['Ciudad de la Costa'],
        'Uruguay|Maldonado':['Punta del Este','Maldonado'],
      },
    };
  }
  return req<GeoCatalog>('/geo/catalog');
}
export type AddGeoCityResult={created:boolean;city?:string;needsConfirmation?:boolean;suggestion?:string};
export async function addGeoCity(
  payload:{country:string;province:string;city:string;force?:boolean},
  session:Session,
):Promise<AddGeoCityResult>{
  if(!base){
    return {created:true,city:payload.city.trim()};
  }
  return req<AddGeoCityResult>('/geo/cities',{method:'POST',body:JSON.stringify(payload)},session.token);
}

export async function trackEvent(name:EventName,property_id?:string,context?:Record<string,unknown>,session?:Session|null){if(!base)return;return req('/events',{method:'POST',body:JSON.stringify({name,property_id,session_id:'web-session',context})},session?.token)}
const BUYER_KEY='propomi-buyer-session';
function getBuyerSession():Session|null{try{const raw=localStorage.getItem(BUYER_KEY);return raw?JSON.parse(raw):null}catch{return null}}
export function setBuyerSession(session:Session){localStorage.setItem(BUYER_KEY,JSON.stringify(session))}
export function clearBuyerIdentity(){localStorage.removeItem(BUYER_KEY);localStorage.removeItem(BUYER_PROFILE_KEY)}
export async function getOrCreateBuyerSession():Promise<Session|null>{if(!base)return getBuyerSession();const existing=getBuyerSession();if(existing)return existing;const r=await req<{token:string;user:Session['user']}>('/auth/guest',{method:'POST'});const session={token:r.token,user:r.user};setBuyerSession(session);return session}

// Perfil de contacto del comprador: se pide UNA sola vez (nunca dentro del
// wizard de oferta) y se reutiliza en todas las acciones de alta intención
// (oferta, visita, consulta). Nunca se expone a la agencia hasta el reveal.
const BUYER_PROFILE_KEY='propomi-buyer-profile';
export function getBuyerProfile():BuyerProfile|null{try{const raw=localStorage.getItem(BUYER_PROFILE_KEY);return raw?JSON.parse(raw):null}catch{return null}}
export function setBuyerProfile(profile:BuyerProfile){localStorage.setItem(BUYER_PROFILE_KEY,JSON.stringify(profile))}

const AGENT_KEY='propomi-agent-session';
export function getAgentSession():Session|null{try{const raw=localStorage.getItem(AGENT_KEY);return raw?JSON.parse(raw):null}catch{return null}}
export function setAgentSession(session:Session){localStorage.setItem(AGENT_KEY,JSON.stringify(session))}
export function clearAgentSession(){localStorage.removeItem(AGENT_KEY)}
export async function saveIntent(property_id:string,intent:string,level:number,data:Intent,session?:Session|null){if(!base)return;const s=session||await getOrCreateBuyerSession();if(!s)throw new Error('Sesión requerida');return req('/intents',{method:'POST',body:JSON.stringify({property_id,intent,level,...data})},s.token)}
export async function createOffer(payload:{property_id:string;amount:number;payment_form:string;capital?:number;timeframe?:string;comment?:string;buyer_name:string;buyer_phone:string;buyer_email?:string;origin?:string},session?:Session|null){if(!base)return {id:`demo-${Date.now()}`,status:'SENT'};const s=session||await getOrCreateBuyerSession();if(!s)throw new Error('Sesión requerida');return req('/offers',{method:'POST',body:JSON.stringify(payload)},s.token)}
export type OffersListResponse=Offer[]|{verificationRequired:true;verificationStatus:string;count:number;offers:[]};
export async function listOffers(session?:Session|null):Promise<OffersListResponse>{
  if(!base)return [];
  const s=session||await getOrCreateBuyerSession();
  if(!s)throw new Error('Sesión requerida');
  return req<OffersListResponse>('/offers',undefined,s.token);
}
export function isOffersRestricted(r:OffersListResponse):r is {verificationRequired:true;verificationStatus:string;count:number;offers:[]}{
  return !!r && !Array.isArray(r) && (r as any).verificationRequired===true;
}

// Espejo de createOffer/listOffers/isOffersRestricted, para pregunta/visita
// calificadas (mismo wizard, mismos pasos 2-4, sin monto obligatorio).
export async function createLead(payload:{property_id:string;intent_type:'QUESTION'|'VISIT';has_proposal?:boolean;amount?:number;payment_form?:string;capital?:number;timeframe?:string;comment?:string;visit_day?:string;visit_slot?:string;buyer_name:string;buyer_phone:string;buyer_email?:string;origin?:string},session?:Session|null){if(!base)return {id:`demo-lead-${Date.now()}`,status:'SENT'};const s=session||await getOrCreateBuyerSession();if(!s)throw new Error('Sesión requerida');return req('/leads',{method:'POST',body:JSON.stringify(payload)},s.token)}
export type LeadsListResponse=Lead[]|{verificationRequired:true;verificationStatus:string;count:number;leads:[]};
export async function listLeads(session?:Session|null):Promise<LeadsListResponse>{
  if(!base)return [];
  const s=session||await getOrCreateBuyerSession();
  if(!s)throw new Error('Sesión requerida');
  return req<LeadsListResponse>('/leads',undefined,s.token);
}
export function isLeadsRestricted(r:LeadsListResponse):r is {verificationRequired:true;verificationStatus:string;count:number;leads:[]}{
  return !!r && !Array.isArray(r) && (r as any).verificationRequired===true;
}
export async function revealLeadContact(leadId:string,session?:Session|null){if(!base)return {buyer_name:'Comprador demo',buyer_phone:'+5491100000000',buyer_email:undefined,method:'demo'};return req<{buyer_name:string;buyer_phone:string;buyer_email?:string;method?:string;already_revealed?:boolean}>(`/leads/${leadId}/reveal`,{method:'POST'},session?.token)}

export async function counterOffer(id:string,amount:number,comment?:string,session?:Session|null){if(!base)return {status:'SENT'};return req(`/offers/${id}/counter`,{method:'POST',body:JSON.stringify({amount,comment})},session?.token)}
export async function offerAction(id:string,action:'accept'|'reject'|'negotiate',session?:Session|null){if(!base)return {status:action};return req(`/offers/${id}/${action}`,{method:'POST'},session?.token)}
export async function revealContact(offerId:string,session?:Session|null){if(!base)return {buyer_name:'Comprador demo',buyer_phone:'+5491100000000',buyer_email:undefined,method:'demo'};return req<{buyer_name:string;buyer_phone:string;buyer_email?:string;method?:string;already_revealed?:boolean}>(`/offers/${offerId}/reveal`,{method:'POST'},session?.token)}
export async function mockCompletePayment(transactionId:string,session?:Session|null){if(!base)return {status:'COMPLETED'};return req<{status:string;buyer_name?:string;buyer_phone?:string;buyer_email?:string}>(`/payments/${transactionId}/mock-complete`,{method:'POST'},session?.token)}
export async function paymentStatus(transactionId:string,session?:Session|null){if(!base)return {status:'PENDING'};return req<{status:string}>(`/payments/${transactionId}/status`,{method:'GET'},session?.token)}
export async function createCheckout(kind:string,session?:Session|null){if(!base)return {checkout_url:'#demo-checkout'};if(!session)throw new Error('Sesión requerida');return req<{checkout_url:string}>('/payments/checkout',{method:'POST',body:JSON.stringify({kind})},session.token)}
export async function requestContact(property_id:string,agency_id:string,session?:Session|null){const s=session||await getOrCreateBuyerSession();const role:Role=s?.user.role==='AGENTE'?'AGENTE':'COMPRADOR';if(!base)return {id:`demo-contact-${Date.now()}`,status:role==='AGENTE'?'SHARED':'REQUESTED',billable:role==='COMPRADOR'};if(!s)throw new Error('Sesión requerida');return req('/contact-requests',{method:'POST',body:JSON.stringify({property_id,agency_id})},s.token)}
export async function shareContact(id:string,session?:Session|null){if(!base)return {status:'SHARED'};return req(`/contact-requests/${id}/share`,{method:'POST'},session?.token)}
export async function getAgencyOpportunities(id:string,session?:Session|null){if(!base)return {active:0,opportunities:[] as Opportunity[],eventCount:0,propertyIds:[] as string[]};return req<{active:number;opportunities:Opportunity[];eventCount:number;propertyIds:string[]}>(`/agencies/${id}/opportunities`,undefined,session?.token)}
export async function getAgency(id:string,session?:Session|null){if(!base)return {id,name:'Agencia demo',city:'Buenos Aires',verified:true,claimed:true,phone:'+5491155550101',verificationStatus:'VERIFIED',instagram:'@agenciademo',websiteLink:null,freeLeadsRemaining:10} as Agency;return req<Agency>(`/agencies/${id}`,undefined,session?.token)}
// Fix etapa 004: antes solo mandaba {name} y el backend soporta también
// instagram / website_link (requeridos para pasar de PENDING a VERIFIED,
// doc 06.2.8) — sin esto, una agencia no tenía forma de completar su
// verificación desde la web. `data` acepta los tres campos, todos opcionales
// salvo name que el backend exige siempre.
export async function updateAgency(id:string,data:{name:string;instagram?:string;website_link?:string},session:Session){if(!base)return {id,name:data.name,verified:true,claimed:true,verificationStatus:'VERIFIED',instagram:data.instagram??null,websiteLink:data.website_link??null} as Agency;return req<Agency>(`/agencies/${id}`,{method:'PATCH',body:JSON.stringify(data)},session.token)}
/** POST /agencies/{id}/subscription — registro/cambio de plan (sin cobro real). */
export async function setAgencySubscription(id:string,plan:string,session:Session){
  if(!base)return {id:'demo',agencyId:id,plan,cupoCiclo:plan==='PLAN_99'?null:plan==='PLAN_50'?60:30,consumidoCiclo:0};
  return req<{id:string;agencyId:string;plan:string;cupoCiclo:number|null;consumidoCiclo:number;fechaRenovacion?:string|null;availableCredit?:number}>(`/agencies/${id}/subscription`,{method:'POST',body:JSON.stringify({plan})},session.token)
}
export async function relinkAgency(id:string,session:Session){if(!base)return {count:0,properties:PROPERTIES.filter(p=>p.agencyId===id),message:'Modo demo: publicaciones ya vinculadas.'};return req<{count:number;properties:Property[];message:string}>(`/agencies/${id}/relink-by-phone`,{method:'POST'},session.token)}

export type PropertyCreatePayload={
  title:string;type?:string;operation?:string;price:number;currency?:string;
  zone:string;city:string;country?:string;province?:string;surface:number;rooms:number;
  bedrooms?:number;bathrooms?:number;parking?:boolean;pool?:boolean;
  balcony?:boolean;pet_friendly?:boolean;credit?:boolean;images?:string[];
  description?:string;
};
// T7.2: alta manual de propiedad (POST /properties). Solo funciona con
// agencia VERIFIED; el backend fuerza agency_id desde la sesión.
export async function createProperty(payload:PropertyCreatePayload,session:Session):Promise<Property>{
  if(!base){
    return {
      id:`demo-p-${Date.now()}`,title:payload.title,type:payload.type||'Departamento',
      operation:(payload.operation as 'Venta')||'Venta',price:payload.price,currency:payload.currency||'USD',
      zone:payload.zone,city:payload.city,surface:payload.surface,rooms:payload.rooms,
      bedrooms:payload.bedrooms??1,bathrooms:payload.bathrooms??1,
      parking:!!payload.parking,pool:!!payload.pool,balcony:!!payload.balcony,
      petFriendly:!!payload.pet_friendly,credit:!!payload.credit,
      freshness:'Publicada por la agencia',originPublishedAt:'Publicada en Propomi',
      source:'Demo',sourceUrl:'#',image:(payload.images&&payload.images[0])||'',
      images:payload.images||[],description:payload.description||'',agencyId:session.user.agency_id,
    };
  }
  return req<Property>('/properties',{method:'POST',body:JSON.stringify(payload)},session.token);
}


/** Sube fotos a R2 vía multipart (campo `files`). Máx 5 total, jpeg/png/webp ≤3MB. */
export async function uploadPropertyImages(
  propertyId: string,
  files: File[],
  session: Session,
): Promise<{id: string; images: string[]; added: string[]}> {
  if (!files.length) throw new Error("Elegí al menos una foto.");
  if (!base) {
    const urls = files.map((f, i) => URL.createObjectURL(f));
    return {id: propertyId, images: urls, added: urls};
  }
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const r = await fetch(`${base}/properties/${propertyId}/images`, {
    method: "POST",
    headers: {Authorization: `Bearer ${session.token}`},
    body: form,
    cache: "no-store",
  });
  if (!r.ok) {
    let message = `Error ${r.status}`;
    try {
      const body = await r.json();
      const detail = body?.detail;
      message = typeof detail === "string" ? detail : (detail?.message || JSON.stringify(detail) || message);
    } catch {
      try { message = (await r.text()) || message; } catch {}
    }
    throw new Error(message);
  }
  return r.json();
}

/** Quita una URL de Property.images y borra en R2 si es nuestro bucket. */
export async function deletePropertyImage(
  propertyId: string,
  url: string,
  session: Session,
): Promise<{id: string; images: string[]}> {
  if (!base) return {id: propertyId, images: []};
  const qs = new URLSearchParams({url});
  return req<{id: string; images: string[]}>(
    `/properties/${propertyId}/images?${qs}`,
    {method: "DELETE"},
    session.token,
  );
}

export async function requestOtp(phone:string){if(!base)return {ok:true,message:'Código demo generado.',dev_code:'123456'};return req<{ok:boolean;message:string;dev_code?:string}>('/auth/otp/request',{method:'POST',body:JSON.stringify({phone})})}

// Alta de agencia desde cero (sin propiedades previas descubiertas por el
// crawler) — resuelve el 403 de /auth/otp/verify cuando el teléfono no
// tiene ninguna Agency asociada todavía.
export async function registerAgency(phone:string,name:string,city:string){
  if(!base)return {agencyId:'demo-agency',message:'Agencia demo creada.'};
  return req<{agencyId:string;message:string}>('/auth/agency/register',{method:'POST',body:JSON.stringify({phone,name,city})});
}
export async function verifyOtp(phone:string,code:string){if(!base)return {token:'demo-token',user:{id:'demo-agent',phone,role:'AGENTE' as const,agency_id:'a1'},relinked_count:2};return req<{token:string;user:Session['user'];relinked_count:number}>('/auth/otp/verify',{method:'POST',body:JSON.stringify({phone,code})})}

// Etapa 2 (sección 6.2.1): verificación de celular del COMPRADOR — mismo
// sistema de códigos que requestOtp ya usa para agentes, pero el endpoint de
// verificación es distinto (/auth/otp/verify-buyer) porque no exige que el
// teléfono esté asociado a una agencia. Reemplaza la sesión guest anónima
// por una sesión atada al celular real ya verificado.
export async function verifyOtpBuyer(phone:string,code:string){if(!base)return {token:'demo-buyer-token',user:{id:'demo-buyer',phone,role:'COMPRADOR' as const,agency_id:''},phone_verified:true};return req<{token:string;user:Session['user'];phone_verified:boolean}>('/auth/otp/verify-buyer',{method:'POST',body:JSON.stringify({phone,code})})}

// Vincula la cuenta de Google (segunda prueba de identidad, además del
// celular) a la sesión de comprador YA verificada por OTP. `session` tiene
// que ser la sesión devuelta por verifyOtpBuyer, no la guest original.
export async function linkGoogleIdentity(idToken:string,session:Session){if(!base)return {email:'demo@propomi.lat',google_verified:true};return req<{email:string;google_verified:boolean}>('/auth/google',{method:'POST',body:JSON.stringify({id_token:idToken})},session.token)}
export async function getAnalytics(session?:Session|null){if(!base)return {properties:PROPERTIES.length,events:0,offers:0,funnel:{}};if(!session)throw new Error('Sesión de agente requerida');return req('/analytics/summary',undefined,session.token)}

// Etapa 3 v2: lee el ranking de demanda (zonas/tipos/operaciones más
// buscados) calculado por el backend sobre los eventos search_performed
// que ya se vienen guardando desde GET /properties (Etapa 3 v1). En modo
// demo (sin NEXT_PUBLIC_API_URL) devuelve un shape vacío pero válido para
// no romper el panel mientras no hay backend real conectado.

export type DemandRequestCreate={zone:string;property_type?:string;rooms_min?:number|null;price_max?:number|null};

/** POST /demand-requests — 403 si plan <$60 (mensaje legible en Error.message). */
export async function createDemandRequest(payload:DemandRequestCreate,session:Session){
  return req<DemandRequest>('/demand-requests',{method:'POST',body:JSON.stringify({
    zone:payload.zone,
    property_type:payload.property_type||'Departamento',
    rooms_min:payload.rooms_min??null,
    price_max:payload.price_max??null,
  })},session.token);
}

export async function listDemandRequests(session:Session){
  return req<DemandRequest[]>('/demand-requests',undefined,session.token);
}

export async function deleteDemandRequest(id:string,session:Session){
  return req<{id:string;active:boolean}>(`/demand-requests/${id}`,{method:'DELETE'},session.token);
}
export async function getAnalyticsDemand(session?:Session|null){if(!base)return {sampleSize:0,topZones:[],topTypes:[],topOperations:[],avgResultCount:null} as DemandSummary;if(!session)throw new Error('Sesión de agente requerida');return req<DemandSummary>('/analytics/demand',undefined,session.token)}

// Etapa 013: panel de administración interno. Usa X-Admin-Key en vez del
// Bearer token de sesión (agente/comprador) — es un mecanismo separado a
// propósito, ver require_admin() en main.py. La clave nunca viaja en la URL.
async function adminReq<T>(path:string,credential:string,init?:RequestInit):Promise<T>{
  // JWT (3 segmentos) ? Bearer; si no, X-Admin-Key (crons/legacy)
  const isJwt = credential.split(".").length === 3;
  const headers: Record<string,string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string,string> || {}),
  };
  if (isJwt) headers["Authorization"] = `Bearer ${credential}`;
  else headers["X-Admin-Key"] = credential;
  const r=await fetch(`${base}${path}`,{...init,headers,cache:"no-store"});
  if(!r.ok){let message=`Error ${r.status}`;try{const body=await r.json();message=typeof body?.detail==='string'?body.detail:message}catch{}const err:any=new Error(message);err.status=r.status;throw err}
  return r.json();
}

// --- Admin panel: login + OTP ? JWT (sessionStorage en el front) ---
export type AdminSession = { token: string; username: string };

export async function adminAuthLogin(username: string, password: string) {
  return req<{ ok: boolean; otpRequired: boolean; phoneHint?: string; smsSent?: boolean; dev_code?: string }>(
    "/admin/auth/login",
    { method: "POST", body: JSON.stringify({ username, password }) },
  );
}

export async function adminAuthVerifyOtp(username: string, code: string) {
  return req<{ token: string; user: { id: string; username: string; role: string }; expiresInHours: number }>(
    "/admin/auth/verify-otp",
    { method: "POST", body: JSON.stringify({ username, code }) },
  );
}

export async function adminAuthMe(token: string) {
  return req<{ ok: boolean; role: string; username?: string }>("/admin/auth/me", undefined, token);
}

export async function getPendingAgencies(adminKey:string):Promise<PendingAgency[]>{if(!base)return [];return adminReq('/admin/agencies/pending',adminKey)}
export async function approveAgency(id:string,adminKey:string,notes?:string):Promise<PendingAgency>{if(!base)return {} as PendingAgency;return adminReq(`/admin/agencies/${id}/approve`,adminKey,{method:'POST',body:notes?JSON.stringify({notes}):undefined})}
export async function rejectAgency(id:string,adminKey:string,notes?:string):Promise<PendingAgency>{if(!base)return {} as PendingAgency;return adminReq(`/admin/agencies/${id}/reject`,adminKey,{method:'POST',body:notes?JSON.stringify({notes}):undefined})}
export async function getReviewQueue(adminKey:string):Promise<{count:number;items:ReviewQueueItem[]}>{if(!base)return {count:0,items:[]};return adminReq('/properties/review-queue',adminKey)}
export async function resolveReviewItem(id:string,action:'confirm_duplicate'|'not_duplicate',adminKey:string){if(!base)return {id,status:action,needsReview:false};return adminReq(`/properties/${id}/review`,adminKey,{method:'POST',body:JSON.stringify({action})})}

// Etapa 015 (subdominios por agencia): resuelve el storefront público
// `/tienda/[slug]` (a su vez destino del rewrite de middleware.ts para
// `{slug}.propomi.lat`). Sin auth, a diferencia de getAgency() que exige
// que el agente esté logueado como dueño de esa agencia — este endpoint
// solo expone lo que ya es público en otras pantallas. En modo demo (sin
// NEXT_PUBLIC_API_URL) resuelve contra las 3 agencias semilla del backend
// para poder probar el flujo sin backend real conectado.
const DEMO_AGENCIES_BY_SLUG:Record<string,Agency>={
  'inmobiliaria-norte':{id:'a1',name:'Inmobiliaria Norte',city:'Buenos Aires',verified:true,claimed:true,verificationStatus:'VERIFIED',slug:'inmobiliaria-norte'},
  'red-urbana':{id:'a2',name:'Red Urbana',city:'Buenos Aires',verified:true,claimed:false,verificationStatus:'VERIFIED',slug:'red-urbana'},
  'urbania':{id:'a3',name:'Urbania',city:'Buenos Aires',verified:false,claimed:false,verificationStatus:'PENDING',slug:'urbania'},
};
export async function getAgencyBySlug(slug:string):Promise<Agency>{
  if(!base){const a=DEMO_AGENCIES_BY_SLUG[slug];if(!a){const err:any=new Error('Agencia no encontrada');err.status=404;throw err}return a}
  return req<Agency>(`/agencies/by-slug/${slug}`);
}


export type OnboardingInfo={
  status:string;
  propertyTitle:string;
  propertyZone:string;
  amount:number;
  currency:string;
  agencyId?:string|null;
  agencyName?:string|null;
  expiresInDays?:number;
  message?:string;
};

// T6.2: resumen público del cold-start (sin teléfonos ni datos de comprador).
export async function getOnboarding(token:string):Promise<OnboardingInfo>{
  if(!base){
    return {
      status:'PENDING',propertyTitle:'Departamento demo',propertyZone:'Palermo',
      amount:120000,currency:'USD',agencyId:'a2',agencyName:'Red Urbana',expiresInDays:14,
    };
  }
  return req<OnboardingInfo>(`/onboarding/${encodeURIComponent(token)}`);
}

export async function completeOnboarding(
  token:string,
  data:{instagram:string;website_link?:string;name?:string},
  session:Session,
):Promise<{status:string;agencyId:string;agencyName:string;verificationStatus:string;message:string}>{
  if(!base){
    return {status:'CLAIMED',agencyId:session.user.agency_id,agencyName:'Demo',verificationStatus:'PENDING',message:'Perfil reclamado (demo).'};
  }
  return req(`/onboarding/${encodeURIComponent(token)}/complete`,{method:'POST',body:JSON.stringify(data)},session.token);
}

const PROP_ORIGIN_KEY='propomi-offer-origin';
export function captureOfferOriginFromUrl(){
  if(typeof window==='undefined')return;
  try{
    const q=new URLSearchParams(window.location.search);
    const o=(q.get('o')||q.get('origin')||'').trim().toLowerCase();
    if(o && /^[a-z0-9][a-z0-9_-]{0,79}$/.test(o)){
      sessionStorage.setItem(PROP_ORIGIN_KEY,o);
    }
  }catch{}
}
export function getOfferOrigin():string|undefined{
  if(typeof window==='undefined')return undefined;
  try{return sessionStorage.getItem(PROP_ORIGIN_KEY)||undefined}catch{return undefined}
}
export function buildShareUrl(propertyId:string,origin:string):string{
  const baseUrl=typeof window!=='undefined'?window.location.origin:'https://propomi.lat';
  const o=origin.trim().toLowerCase().replace(/[^a-z0-9_-]/g,'').slice(0,80);
  return `${baseUrl}/?property=${encodeURIComponent(propertyId)}&o=${encodeURIComponent(o)}`;
}


export type MarketOpportunityZone={
  zone:string;
  agencyListingCount:number;
  searchCount:number;
  budgetMin:number|null;
  budgetMax:number|null;
  budgetMedian:number|null;
  topType:string|null;
  topRooms:string|null;
};
export type MarketOpportunities={days:number;sampleSize:number;zones:MarketOpportunityZone[]};

// T5.7: demanda solo en zonas donde la agencia tiene catálogo (agregado/anónimo).
export async function getMarketOpportunities(agencyId:string,session:Session,days=30):Promise<MarketOpportunities>{
  if(!base)return {days,sampleSize:0,zones:[]};
  return req<MarketOpportunities>(`/agencies/${agencyId}/market-opportunities?days=${days}`,undefined,session.token);
}


export type ListingGroup={
  grouped:boolean;
  listingGroupId?:string|null;
  members?:Property[];
  priceMin?:number;
  priceMax?:number;
};

export async function getListingGroup(propertyId:string):Promise<ListingGroup>{
  if(!base)return {grouped:false};
  return req<ListingGroup>(`/properties/${encodeURIComponent(propertyId)}/group`);
}

/** Deja una sola ficha por listing_group y adjunta rango de precio (T8.7 UX). */
export async function getPropertiesDeduped(filters?:Record<string,string|number|boolean>):Promise<Property[]>{
  const page=await getProperties(filters);
  const items=page.items;
  const seen=new Set<string>();
  const out:Property[]=[];
  const groupCache=new Map<string,ListingGroup>();
  for(const p of items){
    const gid=p.listingGroupId;
    if(!gid){out.push(p);continue}
    if(seen.has(gid))continue;
    seen.add(gid);
    try{
      let g=groupCache.get(gid);
      if(!g){
        g=await getListingGroup(p.id);
        groupCache.set(gid,g);
      }
      if(g.grouped&&g.priceMin!=null&&g.priceMax!=null){
        out.push({
          ...p,
          priceMin:g.priceMin,
          priceMax:g.priceMax,
          groupMemberCount:g.members?.length||1,
        });
      }else{
        out.push(p);
      }
    }catch{
      out.push(p);
    }
  }
  return out;
}
/** Dedup local por listingGroupId — sin fetch. El backend ya manda priceMin/priceMax/groupMemberCount. */
export function dedupeByGroup(items:Property[]):Property[]{
  const seen=new Set<string>();
  const out:Property[]=[];
  for(const p of items){
    const gid=p.listingGroupId;
    if(!gid){out.push(p);continue}
    if(seen.has(gid))continue;
    seen.add(gid);
    out.push(p);
  }
  return out;
}


export type ColdStartTaskItem={
  id:string;
  offerId:string;
  propertyId:string;
  agencyId?:string|null;
  targetPhone:string;
  amount:number;
  currency:string;
  propertyTitle:string;
  propertyZone:string;
  onboardingToken:string;
  onboardingPath:string;
  status:string;
  createdAt?:string|null;
  messageTemplate:string;
};

export async function getColdStartPending(adminKey:string):Promise<ColdStartTaskItem[]>{
  if(!base)return [];
  return adminReq('/admin/cold-start/pending',adminKey);
}

export async function markColdStartSent(id:string,adminKey:string,notes?:string):Promise<{id:string;status:string;sentAt?:string}>{
  if(!base)return {id,status:'SENT',sentAt:new Date().toISOString()};
  return adminReq(`/admin/cold-start/${id}/mark-sent`,adminKey,{
    method:'POST',
    body:notes?JSON.stringify({notes}):undefined,
  });
}

export type AdminAgencyList={count:number;totalMatched:number;items:PendingAgency[]};

export async function listAdminAgencies(
  adminKey:string,
  opts?:{status?:string;q?:string;limit?:number},
):Promise<AdminAgencyList>{
  if(!base)return {count:0,totalMatched:0,items:[]};
  const qs=new URLSearchParams();
  if(opts?.status)qs.set('status',opts.status);
  if(opts?.q)qs.set('q',opts.q);
  if(opts?.limit)qs.set('limit',String(opts.limit));
  const path=`/admin/agencies${qs.toString()?`?${qs}`:''}`;
  return adminReq(path,adminKey);
}

export async function reopenAgency(id:string,adminKey:string,notes?:string):Promise<PendingAgency>{
  if(!base)return {} as PendingAgency;
  return adminReq(`/admin/agencies/${id}/reopen`,adminKey,{
    method:'POST',
    body:notes?JSON.stringify({notes}):undefined,
  });
}


/** Tanda 4: evento de búsqueda anónimo (sin PII). */
export async function trackSearchPerformed(filters:{
  zone?:string; tipo?:string; type?:string; ambientes?:number; rooms?:number;
  precio_min?:number; precio_max?:number; min_price?:number; max_price?:number;
}){
  if(!base)return;
  try{
    await fetch(`${base}/events/search_performed`,{
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify(filters),
    });
  }catch{/* no bloquear UI */}
}
