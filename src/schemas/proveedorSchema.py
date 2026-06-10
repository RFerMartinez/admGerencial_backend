# src/schemas/proveedorSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from datetime import datetime

class DeudaProveedorResponse(BaseModel):
    cuenta_id: int
    cuenta_codigo: str
    proveedor_cuenta: str
    saldo_pendiente: float
    
    model_config = ConfigDict(from_attributes=True)

MetodoPago = Literal["Efectivo", "Transferencia"]

class PagoProveedorCreate(BaseModel):
    fecha: datetime = Field(..., description="Fecha y hora del pago")
    cuenta_proveedor_id: int = Field(..., description="ID de la cuenta contable del proveedor (Pasivo)")
    monto_pagado: float = Field(..., gt=0, description="Monto entregado al proveedor")
    metodo_pago: MetodoPago = Field(..., description="Medio por el cual se cancela la deuda")
    observaciones: Optional[str] = Field(None, description="Nota adicional para el asiento (Opcional)")

class PagoProveedorResponse(BaseModel):
    asiento_id: int
    mensaje: str = "Pago registrado y contabilizado exitosamente."