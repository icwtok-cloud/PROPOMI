from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, String, Integer, Float, Boolean, DateTime, Text, JSON, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./propomi.db")
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

class Base(DeclarativeBase): pass
class Property(Base):
    __tablename__ = "properties"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(60), default="Departamento")
    operation: Mapped[str] = mapped_column(String(20), default="Venta")
    price: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    zone: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100), default="Argentina")
    surface: Mapped[float] = mapped_column(Float)
    rooms: Mapped[int] = mapped_column(Integer)
    bedrooms: Mapped[int] = mapped_column(Integer, default=1)
    bathrooms: Mapped[int] = mapped_column(Integer, default=1)
    parking: Mapped[bool] = mapped_column(Boolean, default=False)
    pool: Mapped[bool] = mapped_column(Boolean, default=False)
    balcony: Mapped[bool] = mapped_column(Boolean, default=False)
    pet_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
    credit: Mapped[bool] = mapped_column(Boolean, default=False)
    freshness: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(160))
    source_url: Mapped[str] = mapped_column(String(500), default="#")
    image: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str] = mapped_column(Text)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80))
    property_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    agency_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    context: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Agency(Base):
    __tablename__ = "agencies"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    city: Mapped[str] = mapped_column(String(100))
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    claimed: Mapped[bool] = mapped_column(Boolean, default=False)

class IntentProfile(Base):
    __tablename__ = "intent_profiles"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    level: Mapped[int] = mapped_column(Integer, default=1)
    intent: Mapped[str] = mapped_column(String(40), default="VIEW")
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    capital: Mapped[float | None] = mapped_column(Float, nullable=True)
    financing: Mapped[str | None] = mapped_column(String(30), nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(60), nullable=True)
    decision_maker: Mapped[str | None] = mapped_column(String(60), nullable=True)
    alternatives: Mapped[bool] = mapped_column(Boolean, default=False)
    contact_shared: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Offer(Base):
    __tablename__ = "offers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    payment_form: Mapped[str] = mapped_column(String(30))
    capital: Mapped[float | None] = mapped_column(Float, nullable=True)
    timeframe: Mapped[str | None] = mapped_column(String(60), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class CounterOffer(Base):
    __tablename__ = "counter_offers"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    offer_id: Mapped[str] = mapped_column(String(40))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(8), default="USD")
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="SENT")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class ContactRequest(Base):
    __tablename__ = "contact_requests"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    agency_id: Mapped[str] = mapped_column(String(40))
    user_id: Mapped[str] = mapped_column(String(40))
    property_id: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(30), default="REQUESTED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

Base.metadata.create_all(engine)

app = FastAPI(title="Propomi API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","), allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DEMO = [
{"id":"p1","title":"Departamento luminoso 2 ambientes","type":"Departamento","operation":"Venta","price":118000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":45,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":False,"pool":False,"balcony":True,"pet_friendly":True,"credit":False,"freshness":"Detectada hace 2 días","source":"Inmobiliaria Norte","source_url":"#","image":"https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1000&q=85","description":"Unidad renovada, muy luminosa y con balcón.","agency_id":"a1"},
{"id":"p2","title":"Departamento moderno con balcón","type":"Departamento","operation":"Venta","price":120000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":43,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":True,"pool":False,"balcony":True,"pet_friendly":False,"credit":True,"freshness":"Actualizada hace 4 días","source":"Red Urbana","source_url":"#","image":"https://images.unsplash.com/photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1000&q=85","description":"Edificio moderno con cochera y amenities.","agency_id":"a2"},
{"id":"p3","title":"2 ambientes amplio a estrenar","type":"Departamento","operation":"Venta","price":125000,"currency":"USD","zone":"Palermo","city":"Buenos Aires","surface":48,"rooms":2,"bedrooms":1,"bathrooms":1,"parking":False,"pool":True,"balcony":True,"pet_friendly":True,"credit":False,"freshness":"Detectada hace 6 días","source":"Habitar","source_url":"#","image":"https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1000&q=85","description":"A estrenar, excelente distribución.","agency_id":"a1"},
{"id":"p4","title":"Departamento 3 ambientes con patio","type":"Departamento","operation":"Venta","price":138000,"currency":"USD","zone":"Villa Crespo","city":"Buenos Aires","surface":62,"rooms":3,"bedrooms":2,"bathrooms":1,"parking":False,"pool":False,"balcony":False,"pet_friendly":True,"credit":True,"freshness":"Actualizada hace 1 día","source":"Urbania","source_url":"#","image":"https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?auto=format&fit=crop&w=1000&q=85","description":"Patio y ambientes amplios para familia.","agency_id":"a3"},
]

class EventIn(BaseModel): name: str; property_id: str|None=None; user_id: str|None=None; agency_id: str|None=None; session_id: str|None=None; context: dict[str,Any]=Field(default_factory=dict)
class OfferIn(BaseModel): user_id: str="demo-buyer"; property_id: str; amount: float; payment_form: str="MIXED"; capital: float|None=None; timeframe: str|None=None; comment: str|None=None
class CounterIn(BaseModel): amount: float; comment: str|None=None
class ContactIn(BaseModel): agency_id: str; user_id: str="demo-buyer"; property_id: str
class IntentIn(BaseModel): user_id: str="demo-buyer"; property_id: str; intent: str; level: int; budget: float|None=None; capital: float|None=None; financing: str|None=None; timeframe: str|None=None; decision_maker: str|None=None; alternatives: bool=False

@app.get("/health")
def health(): return {"status":"ok","service":"propomi-api","version":"1.0.0"}

def ensure_seed(db: Session):
    if db.scalar(select(Property.id).limit(1)) is None:
        for row in DEMO: db.add(Property(**row))
        db.add_all([Agency(id="a1",name="Inmobiliaria Norte",city="Buenos Aires",verified=True,claimed=True),Agency(id="a2",name="Red Urbana",city="Buenos Aires",verified=True,claimed=False),Agency(id="a3",name="Urbania",city="Buenos Aires",verified=False,claimed=False)])
        db.commit()

def prop_dict(p: Property):
    return {"id":p.id,"title":p.title,"type":p.type,"operation":p.operation,"price":p.price,"currency":p.currency,"zone":p.zone,"city":p.city,"country":p.country,"surface":p.surface,"rooms":p.rooms,"bedrooms":p.bedrooms,"bathrooms":p.bathrooms,"parking":p.parking,"pool":p.pool,"balcony":p.balcony,"petFriendly":p.pet_friendly,"credit":p.credit,"freshness":p.freshness,"source":p.source,"sourceUrl":p.source_url,"image":p.image,"description":p.description,"agencyId":p.agency_id,"detectedAt":p.detected_at.isoformat() if p.detected_at else None,"lastSeenAt":p.last_seen_at.isoformat() if p.last_seen_at else None}

@app.get("/properties")
def properties(zone: str|None=None, operation: str|None=None, rooms: int|None=None, max_price: float|None=None, parking: bool|None=None, credit: bool|None=None):
    with Session(engine) as db:
        ensure_seed(db); q=select(Property)
        if zone: q=q.where(Property.zone==zone)
        if operation: q=q.where(Property.operation==operation)
        if rooms: q=q.where(Property.rooms==rooms)
        if max_price: q=q.where(Property.price<=max_price)
        if parking: q=q.where(Property.parking.is_(True))
        if credit: q=q.where(Property.credit.is_(True))
        return [prop_dict(p) for p in db.scalars(q).all()]

@app.get("/properties/{property_id}")
def property_detail(property_id: str):
    with Session(engine) as db:
        ensure_seed(db); p=db.get(Property,property_id)
        if not p: raise HTTPException(404,"Propiedad no encontrada")
        return prop_dict(p)

@app.post("/events",status_code=201)
def create_event(payload: EventIn):
    with Session(engine) as db:
        row=Event(**payload.model_dump()); db.add(row); db.commit(); return {"ok":True,"id":row.id}

@app.get("/events/funnel")
def funnel():
    names=["property_view","property_save","property_compare","property_question","visit_request","offer_created","negotiation_started","contact_shared","operation_advanced"]
    with Session(engine) as db:
        rows=db.scalars(select(Event)).all(); return {n:sum(1 for e in rows if e.name==n) for n in names}

@app.post("/intents",status_code=201)
def upsert_intent(payload: IntentIn):
    with Session(engine) as db:
        row=IntentProfile(id=f"i-{payload.user_id}-{payload.property_id}",**payload.model_dump()); old=db.get(IntentProfile,row.id)
        if old:
            for k,v in payload.model_dump().items(): setattr(old,k,v)
            old.updated_at=datetime.now(timezone.utc)
        else: db.add(row)
        db.commit(); return {"ok":True,"intent":row.intent,"level":row.level}

@app.post("/offers",status_code=201)
def create_offer(payload: OfferIn):
    with Session(engine) as db:
        if not db.get(Property,payload.property_id): raise HTTPException(404,"Propiedad no encontrada")
        oid=f"off-{int(datetime.now().timestamp()*1000)}"; row=Offer(id=oid,**payload.model_dump()); db.add(row)
        db.add(Event(name="offer_created",property_id=payload.property_id,user_id=payload.user_id,context={"offer_id":oid,"amount":payload.amount}))
        db.commit(); return {"id":oid,"status":row.status}

@app.get("/offers")
def list_offers(user_id: str|None=None, status: str|None=None):
    with Session(engine) as db:
        q=select(Offer)
        if user_id:q=q.where(Offer.user_id==user_id)
        if status:q=q.where(Offer.status==status)
        return [o.__dict__ | {"_sa_instance_state":None} for o in db.scalars(q).all()]

@app.post("/offers/{offer_id}/counter",status_code=201)
def counter_offer(offer_id:str,payload:CounterIn):
    with Session(engine) as db:
        o=db.get(Offer,offer_id)
        if not o: raise HTTPException(404,"Oferta no encontrada")
        o.status="COUNTERED"; cid=f"co-{int(datetime.now().timestamp()*1000)}"; c=CounterOffer(id=cid,offer_id=offer_id,**payload.model_dump()); db.add(c)
        db.add(Event(name="counter_offer_created",property_id=o.property_id,user_id=o.user_id,context={"offer_id":offer_id,"amount":payload.amount})); db.commit(); return {"id":cid,"status":c.status}

@app.post("/offers/{offer_id}/{action}")
def offer_action(offer_id:str,action:str):
    allowed={"accept":"ACCEPTED","reject":"REJECTED","negotiate":"NEGOTIATION"}
    if action not in allowed: raise HTTPException(400,"Acción inválida")
    with Session(engine) as db:
        o=db.get(Offer,offer_id)
        if not o: raise HTTPException(404,"Oferta no encontrada")
        o.status=allowed[action]; event="negotiation_started" if action=="negotiate" else "offer_status_changed"; db.add(Event(name=event,property_id=o.property_id,user_id=o.user_id,context={"offer_id":offer_id,"action":action})); db.commit(); return {"ok":True,"status":o.status}

@app.post("/contact-requests",status_code=201)
def contact_request(payload:ContactIn):
    with Session(engine) as db:
        cid=f"cr-{int(datetime.now().timestamp()*1000)}"; row=ContactRequest(id=cid,**payload.model_dump()); db.add(row); db.add(Event(name="contact_requested",property_id=payload.property_id,user_id=payload.user_id,agency_id=payload.agency_id)); db.commit(); return {"id":cid,"status":row.status,"message":"La solicitud fue enviada. El comprador decide si comparte sus datos."}

@app.post("/contact-requests/{request_id}/share")
def share_contact(request_id:str):
    with Session(engine) as db:
        r=db.get(ContactRequest,request_id)
        if not r: raise HTTPException(404,"Solicitud no encontrada")
        r.status="SHARED"; db.add(Event(name="contact_shared",property_id=r.property_id,user_id=r.user_id,agency_id=r.agency_id)); db.commit(); return {"ok":True,"status":r.status}

@app.get("/agencies/{agency_id}/opportunities")
def opportunities(agency_id:str):
    with Session(engine) as db:
        events=db.scalars(select(Event).where(Event.agency_id==agency_id)).all()
        offers=db.scalars(select(Offer)).all()
        grouped=[]
        for o in offers:
            p=db.get(Property,o.property_id)
            if p and p.agency_id==agency_id:
                grouped.append({"id":o.id,"type":"OFFER","property":p.title,"propertyId":p.id,"amount":o.amount,"status":o.status,"personalData":"HIDDEN"})
        return {"active":len(grouped),"opportunities":grouped,"eventCount":len(events)}

@app.get("/agencies/{agency_id}")
def agency(agency_id:str):
    with Session(engine) as db:
        a=db.get(Agency,agency_id)
        if not a: raise HTTPException(404,"Agencia no encontrada")
        return {"id":a.id,"name":a.name,"city":a.city,"verified":a.verified,"claimed":a.claimed}

@app.post("/agencies/{agency_id}/claim")
def claim_agency(agency_id:str):
    with Session(engine) as db:
        a=db.get(Agency,agency_id)
        if not a: raise HTTPException(404,"Agencia no encontrada")
        a.claimed=True; db.commit(); return {"ok":True,"status":"VERIFICATION_PENDING"}

@app.get("/analytics/summary")
def analytics():
    with Session(engine) as db:
        props=db.scalars(select(Property)).all(); events=db.scalars(select(Event)).all(); offers=db.scalars(select(Offer)).all()
        return {"properties":len(props),"events":len(events),"offers":len(offers),"funnel":{"views":sum(e.name=="property_view" for e in events),"saves":sum(e.name=="property_save" for e in events),"comparisons":sum(e.name=="property_compare" for e in events),"questions":sum(e.name=="property_question" for e in events),"visits":sum(e.name=="visit_request" for e in events),"offers":len(offers),"negotiations":sum(e.name=="negotiation_started" for e in events),"contacts":sum(e.name=="contact_shared" for e in events)}}
