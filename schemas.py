"""
Database Schemas for Direct Transport Platform (España)

Each Pydantic model maps to a MongoDB collection (lowercased class name).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime


class TransportUser(BaseModel):
    """
    Users of the platform: clientes y transportistas
    Collection: "transportuser"
    """
    role: Literal["cliente", "transportista"] = Field(..., description="Tipo de usuario")
    name: str = Field(..., min_length=2, max_length=120)
    email: Optional[EmailStr] = None
    phone: str = Field(..., min_length=7, max_length=20)
    province: Optional[str] = Field(None, description="Provincia principal de operación")
    vehicle_types: Optional[List[str]] = Field(None, description="Solo para transportistas: tipos de vehículo")
    whatsapp_number: Optional[str] = Field(None, description="Número de WhatsApp")
    rating: Optional[float] = Field(default=None, ge=0, le=5)
    is_active: bool = True


class TransportRequest(BaseModel):
    """
    Solicitudes de transporte publicadas por clientes
    Collection: "transportrequest"
    """
    customer_id: Optional[str] = Field(None, description="ID del cliente que crea la solicitud")
    pickup_address: str
    pickup_city: str
    dropoff_address: str
    dropoff_city: str
    date_iso: str = Field(..., description="Fecha/Hora ISO 8601")
    item_type: str = Field(..., description="Tipo de carga: muebles, paquetes, moto, etc.")
    size: str = Field(..., description="Tamaño/volumen aproximado")
    notes: Optional[str] = None
    whatsapp_number: Optional[str] = Field(None, description="Número de WhatsApp para coordinar")
    status: Literal["pendiente", "asignado", "en_ruta", "entregado", "cancelado"] = "pendiente"


class StatusUpdate(BaseModel):
    """Actualizar estado de una solicitud"""
    status: Literal["pendiente", "asignado", "en_ruta", "entregado", "cancelado"]
    last_location: Optional[str] = None
    updated_by: Optional[str] = None  # user id
    timestamp: Optional[datetime] = None


class TransportistaQuery(BaseModel):
    province: Optional[str] = None
    vehicle_type: Optional[str] = None
