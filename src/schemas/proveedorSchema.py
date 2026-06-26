# src/schemas/proveedorSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime


class DeudaProveedorResponse(BaseModel):
    id: int
    nombre: str
    cuit: Optional[str] = None
    saldo_pendiente: float

    model_config = ConfigDict(from_attributes=True)


MetodoPago = Literal["Efectivo", "Transferencia"]


class PagoProveedorCreate(BaseModel):
    fecha: datetime = Field(...)
    proveedor_id: int = Field(..., gt=0)
    monto_pagado: float = Field(..., gt=0)
    metodo_pago: MetodoPago = Field(...)
    observaciones: Optional[str] = Field(None)
    tipo_comprobante: str = Field(...)
    nro_comprobante_recibido: str = Field(...)
    comprobante_padre_id: Optional[int] = Field(default=None)


class PagoProveedorResponse(BaseModel):
    asiento_id: int
    mensaje: str = "Pago registrado y contabilizado exitosamente."
