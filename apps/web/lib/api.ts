import {Agency,BuyerProfile,DemandSummary,EventName,Intent,Offer,Opportunity,Property,Role,Session} from './types';

import {PROPERTIES} from './data';
const base=process.env.NEXT_PUBLIC_API_URL;
async function req<T>(path:string,init?:RequestInit,token?:string):Promise<T>{const r=await fetch(`${base}${path}`,{...init,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{}) ,...(init?.headers||{})},cache:'no-store'});if(!r.ok){let message=`Error ${r.status}`;let detail:any=undefined;try{const body=await r.json();detail=body?.detail;message=typeof detail==='string'?detail:(detail?.message||JSON.stringify(detail)||message)}catch{try{message=await r.text()||message}catch{}}const err:any=new Error(message);err.status=r.status;err.detail=detail;throw err}return r.json()}
export async function getProperties(filters?:Record<string,string|number|boolean>){if(!base)return PROPERTIES;const qs=new URLSearchParams();Object.entries(filters||{}).forEach(([k,v])=>v!==''&&v!==undefined&&qs.set(k,String(v)));return req<Property[]>(`/properties?${qs}`)}
export async function getProperty(id:string){if(!base)return PROPERTIES.find(p=>p.id===id)!;return req<Property>(`/properties/${id}`)}
export async function trackEvent(name:EventName,property_id?:string,context?:Record<string,unknown>,session?:Session|null){if(!base)return;return req('/events',{method:'POST',body:JSON.stringify({name,property_id,session_id:'web-session',context})},session?.token)}
const BUYER_KEY='propomi-buyer-session';
function getBuyerSession():Session|null{try{const raw=localStorage.getItem(BUYER_KEY);return raw?JSON.parse(raw):null}catch{return null}}
export function setBuyerSession(session:Session){localStorage.setItem(BUYER_KEY,JSON.stringify(session))}
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
export async function createOffer(payload:{property_id:string;amount:number;payment_form:string;capital?:number;timeframe?:string;comment?:string;buyer_name:string;buyer_phone:string;buyer_email?:string},session?:Session|null){if(!base)return {id:`demo-${Date.now()}`,status:'SENT'};const s=session||await getOrCreateBuyerSession();if(!s)throw new Error('Sesión requerida');return req('/offers',{method:'POST',body:JSON.stringify(payload)},s.token)}
export async function listOffers(session?:Session|null){if(!base)return [];const s=session||await getOrCreateBuyerSession();if(!s)throw new Error('Sesión requerida');return req<Offer[]>('/offers',undefined,s.token)}
export async function counterOffer(id:string,amount:number,comment?:string,session?:Session|null){if(!base)return {status:'SENT'};return req(`/offers/${id}/counter`,{method:'POST',body:JSON.stringify({amount,comment})},session?.token)}
export async function offerAction(id:string,action:'accept'|'reject'|'negotiate',session?:Session|null){if(!base)return {status:action};return req(`/offers/${id}/${action}`,{method:'POST'},session?.token)}
export async function revealContact(offerId:string,session?:Session|null){if(!base)return {buyer_name:'Comprador demo',buyer_phone:'+5491100000000',buyer_email:undefined,method:'demo'};return req<{buyer_name:string;buyer_phone:string;buyer_email?:string;method?:string;already_revealed?:boolean}>(`/offers/${offerId}/reveal`,{method:'POST'},session?.token)}
export async function mockCompletePayment(transactionId:string,session?:Session|null){if(!base)return {status:'COMPLETED'};return req<{status:string;buyer_name?:string;buyer_phone?:string;buyer_email?:string}>(`/payments/${transactionId}/mock-complete`,{method:'POST'},session?.token)}
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
export async function relinkAgency(id:string,session:Session){if(!base)return {count:0,properties:PROPERTIES.filter(p=>p.agencyId===id),message:'Modo demo: publicaciones ya vinculadas.'};return req<{count:number;properties:Property[];message:string}>(`/agencies/${id}/relink-by-phone`,{method:'POST'},session.token)}
export async function requestOtp(phone:string){if(!base)return {ok:true,message:'Código demo generado.',dev_code:'123456'};return req<{ok:boolean;message:string;dev_code?:string}>('/auth/otp/request',{method:'POST',body:JSON.stringify({phone})})}
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
export async function getAnalyticsDemand(session?:Session|null){if(!base)return {sampleSize:0,topZones:[],topTypes:[],topOperations:[],avgResultCount:null} as DemandSummary;if(!session)throw new Error('Sesión de agente requerida');return req<DemandSummary>('/analytics/demand',undefined,session.token)}
