# src/schemas/compraSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal
from datetime import date

# Definimos los tipos permitidos para evitar errores de tipeo desde el frontend
TipoComprobante = Literal["Factura A", "Factura B", "Factura C", "Ticket", "Pagaré"]
MetodoPago = Literal["Efectivo", "Transferencia", "Tarjeta", "Cuenta Corriente"]

class CompraDetalle(BaseModel):
    producto_id: int = Field(..., description="ID del producto comprado")
    cantidad: int = Field(..., gt=0, description="Cantidad adquirida")
    costo_unitario: float = Field(..., ge=0, description="Costo al que nos vendió el proveedor")

class CompraCreate(BaseModel):
    fecha: date = Field(..., description="Fecha del comprobante")
    metodo_pago: MetodoPago = Field(..., description="Forma de cancelación")
    tipo_comprobante: TipoComprobante = Field(..., description="Documento que respalda la compra")
    nro_comprobante: str = Field(default="S/N", max_length=50)
    total: float = Field(..., gt=0, description="Total facturado")
    detalles: List[CompraDetalle] = Field(..., min_length=1, description="Lista de productos comprados")
    
    model_config = ConfigDict(populate_by_name=True)

class CompraResponse(BaseModel):
    id: int
    fecha: date
    total: float
    asiento_id: int
    mensaje: str = "Compra registrada, stock actualizado y contabilizada exitosamente."

    model_config = ConfigDict(from_attributes=True)

