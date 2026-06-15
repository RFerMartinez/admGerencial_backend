# src/schemas/documentoSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import date

# --- GET: Listado Universal ---
class ItemOriginal(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: float

class DocumentoListResponse(BaseModel):
    id: int
    tipo_operacion: str
    fecha_emision: date
    tipo_comprobante: str
    nro_comprobante: str
    entidad_nombre: str
    total: float
    items_originales: List[ItemOriginal]

# --- POST: Notas de Crédito / Débito ---
class ItemAfectado(BaseModel):
    producto_id: int = Field(..., description="ID del producto afectado")
    cantidad: int = Field(..., gt=0, description="Cantidad devuelta o recargada")
    precio_unitario: float = Field(..., ge=0, description="Precio unitario o costo")

class NotaVentaCreate(BaseModel):
    comprobante_padre_id: int
    tipo_comprobante: str
    motivo: str
    total_modificado: float = Field(..., gt=0)
    items_afectados: List[ItemAfectado] = []

class NotaCompraCreate(BaseModel):
    comprobante_padre_id: int
    tipo_comprobante: str
    nro_comprobante_recibido: str
    motivo: str
    total_modificado: float = Field(..., gt=0)
    items_afectados: List[ItemAfectado] = []

class NotaResponse(BaseModel):
    id: int
    asiento_id: int
    nro_comprobante: str
    mensaje: str

    model_config = ConfigDict(from_attributes=True)

