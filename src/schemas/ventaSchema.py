# src/schemas/ventaSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Literal
from datetime import datetime
from datetime import date as dt_date

# Restringimos las opciones aceptadas por el validador
TipoMetodoPago = Literal["efectivo", "transferencia"]

class VentaItem(BaseModel):
    producto_id: int = Field(..., alias="id", description="ID del producto vendido")
    nombre: str = Field(..., min_length=1, max_length=150, description="Nombre comercial del producto")
    cantidad: int = Field(..., gt=0, description="Cantidad de unidades vendidas")
    precio_unitario: float = Field(..., alias="precio", ge=0, description="Precio de venta unitario")

    model_config = ConfigDict(populate_by_name=True)


class VentaCreate(BaseModel):
    fecha: datetime = Field(..., description="Fecha y hora de la transacción")
    metodo_pago: TipoMetodoPago = Field(..., alias="metodoPago", description="Forma de pago recibida")
    monto_recibido: float = Field(..., alias="montoRecibido", ge=0, description="Dinero entregado por el comprador")
    vuelto: float = Field(..., ge=0, description="Cambio entregado")
    total: float = Field(..., gt=0, description="Monto final neto de la venta")
    items: List[VentaItem] = Field(..., min_length=1, description="Detalle de productos incluidos")

    model_config = ConfigDict(populate_by_name=True)


class VentaResponse(BaseModel):
    id: int
    fecha: dt_date
    total: float
    asiento_id: int
    mensaje: str = "Venta registrada y contabilizada exitosamente."

    model_config = ConfigDict(from_attributes=True)

