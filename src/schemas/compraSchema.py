# src/schemas/compraSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import date

class CompraDetalle(BaseModel):
    producto_id: int = Field(..., description="ID del producto comprado")
    cantidad: int = Field(..., gt=0, description="Cantidad adquirida")
    costo_unitario: float = Field(..., ge=0, description="Costo al que nos vendió el proveedor")

class CompraCreate(BaseModel):
    fecha: date = Field(..., description="Fecha del comprobante")
    metodo_pago: str = Field(..., description="Ej: Efectivo, Transferencia")
    tipo_comprobante: str = Field(default="Ticket", max_length=50)
    nro_comprobante: str = Field(default="S/N", max_length=50)
    total: float = Field(..., gt=0, description="Total facturado")
    detalles: List[CompraDetalle] = Field(..., min_length=1, description="Lista de productos comprados")
    
    # Aceptamos tanto snake_case como camelCase por si el frontend lo envía distinto
    model_config = ConfigDict(populate_by_name=True)

class CompraResponse(BaseModel):
    id: int
    fecha: date
    total: float
    asiento_id: int
    mensaje: str = "Compra registrada, stock actualizado y contabilizada exitosamente."

    model_config = ConfigDict(from_attributes=True)

