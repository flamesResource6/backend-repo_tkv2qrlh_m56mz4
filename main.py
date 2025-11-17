import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import TransportUser, TransportRequest, StatusUpdate, TransportistaQuery

app = FastAPI(title="Direct Transport ES API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Direct Transport ES Backend listo"}


@app.get("/test")
def test_database():
    """Check DB connectivity and list collections"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = os.getenv("DATABASE_NAME") or "❌ Not Set"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections
                response["database"] = "✅ Connected & Working"
                response["connection_status"] = "Connected"
            except Exception as e:
                response["database"] = f"⚠️ Connected but error: {str(e)[:80]}"
        else:
            response["database"] = "❌ Database not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:120]}"
    return response


# Helpers
class IdResponse(BaseModel):
    id: str


def _to_str_id(doc):
    if isinstance(doc, dict) and doc.get("_id"):
        doc["id"] = str(doc.pop("_id"))
    return doc


# Users (clientes y transportistas)
@app.post("/api/users", response_model=IdResponse)
def create_user(user: TransportUser):
    user_id = create_document("transportuser", user)
    return {"id": user_id}


@app.get("/api/transportistas")
def list_transportistas(province: Optional[str] = None, vehicle_type: Optional[str] = None):
    query = {}
    if province:
        query["province"] = province
    if vehicle_type:
        query["vehicle_types"] = {"$in": [vehicle_type]}
    docs = get_documents("transportuser", query, limit=50)
    # filter role
    docs = [d for d in docs if d.get("role") == "transportista"]
    return [_to_str_id(d) for d in docs]


# Requests
@app.post("/api/requests", response_model=IdResponse)
def create_request(req: TransportRequest):
    req_id = create_document("transportrequest", req)
    return {"id": req_id}


@app.get("/api/requests")
def list_requests(status: Optional[str] = None, city: Optional[str] = None):
    query = {}
    if status:
        query["status"] = status
    if city:
        query["$or"] = [{"pickup_city": city}, {"dropoff_city": city}]
    docs = get_documents("transportrequest", query, limit=100)
    return [_to_str_id(d) for d in docs]


@app.patch("/api/requests/{request_id}/status")
def update_request_status(request_id: str, update: StatusUpdate):
    if db is None:
        raise HTTPException(status_code=500, detail="DB not configured")
    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request id")

    update_doc = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    update_doc["updated_at"] = db.command({"serverStatus": 1}).get("localTime")

    res = db["transportrequest"].update_one({"_id": oid}, {"$set": update_doc})
    if res.matched_count == 0:
        raise HTTPException(status_code=404, detail="Request not found")
    doc = db["transportrequest"].find_one({"_id": oid})
    return _to_str_id(doc)


# Lightweight booking intent with WhatsApp handoff
class BookingIntent(BaseModel):
    name: str
    phone: str
    whatsapp_number: Optional[str] = None
    pickup_city: str
    dropoff_city: str
    item_type: str
    date_iso: str


@app.post("/api/bookings/intent", response_model=IdResponse)
def create_booking_intent(payload: BookingIntent):
    doc = payload.model_dump()
    doc["type"] = "booking_intent"
    inserted_id = create_document("lead", doc)
    return {"id": inserted_id}


# Optional helper to generate WhatsApp deeplink (frontend can also do it)
@app.get("/api/whatsapp-link")
def whatsapp_link(name: str, phone: str, pickup: str, dropoff: str, date: str, item: str):
    import urllib.parse
    base = "https://wa.me/" + phone.replace("+", "").replace(" ", "")
    text = f"Hola, soy {name}. Quiero enviar {item} de {pickup} a {dropoff} el {date}. ¿Disponibilidad?"
    return {"url": f"{base}?text={urllib.parse.quote(text)}"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
