import {Property,EventName,Intent,Offer} from './types';
import {PROPERTIES} from './data';
const base=process.env.NEXT_PUBLIC_API_URL;
async function req<T>(path:string,init?:RequestInit):Promise<T>{const r=await fetch(`${base}${path}`,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})},cache:'no-store'});if(!r.ok)throw new Error(await r.text());return r.json()}
export async function getProperties(filters?:Record<string,string|number|boolean>){if(!base)return PROPERTIES;const qs=new URLSearchParams();Object.entries(filters||{}).forEach(([k,v])=>v!==''&&v!==undefined&&qs.set(k,String(v)));return req<Property[]>(`/properties?${qs}`)}
export async function getProperty(id:string){if(!base)return PROPERTIES.find(p=>p.id===id)!;return req<Property>(`/properties/${id}`)}
export async function trackEvent(name:EventName,property_id?:string,context?:Record<string,unknown>){if(!base)return;return req('/events',{method:'POST',body:JSON.stringify({name,property_id,user_id:'demo-buyer',session_id:'demo-session',context})})}
export async function saveIntent(property_id:string,intent:string,level:number,data:Intent){if(!base)return;return req('/intents',{method:'POST',body:JSON.stringify({user_id:'demo-buyer',property_id,intent,level,...data})})}
export async function createOffer(payload:{property_id:string;amount:number;payment_form:string;capital?:number;timeframe?:string;comment?:string}){if(!base)return {id:`demo-${Date.now()}`,status:'SENT'};return req('/offers',{method:'POST',body:JSON.stringify(payload)})}
export async function listOffers(){if(!base)return [];return req<Offer[]>('/offers?user_id=demo-buyer')}
export async function counterOffer(id:string,amount:number,comment?:string){if(!base)return {status:'SENT'};return req(`/offers/${id}/counter`,{method:'POST',body:JSON.stringify({amount,comment})})}
export async function offerAction(id:string,action:'accept'|'reject'|'negotiate'){if(!base)return {status:action};return req(`/offers/${id}/${action}`,{method:'POST'})}
export async function requestContact(property_id:string,agency_id:string){if(!base)return {id:`demo-contact-${Date.now()}`,status:'REQUESTED'};return req('/contact-requests',{method:'POST',body:JSON.stringify({property_id,agency_id,user_id:'demo-buyer'})})}
export async function shareContact(id:string){if(!base)return {status:'SHARED'};return req(`/contact-requests/${id}/share`,{method:'POST'})}
export async function getAgencyOpportunities(id:string){if(!base)return {active:0,opportunities:[],eventCount:0};return req(`/agencies/${id}/opportunities`)}
export async function getAnalytics(){if(!base)return {properties:PROPERTIES.length,events:0,offers:0,funnel:{}};return req('/analytics/summary')}
