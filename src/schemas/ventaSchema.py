from pydantic import BaseModel, Field, ConfigDict
from typing import List
from datetime import datetime
from datetime import date as dt_date

class VentaItem(BaseModel):
    # Traducimos "id" a "producto_id" y "precio" a "precio_unitario"
    producto_id: int = Field(..., alias="id", description="ID del producto vendido")
    nombre: str = Field(..., min_length=1, max_length=150, description="Nombre comercial del producto")  # <-- Campo agregado
    cantidad: int = Field(..., gt=0, description="Cantidad de unidades vendidas")
    precio_unitario: float = Field(..., alias="precio", ge=0, description="Precio de venta unitario")

    model_config = ConfigDict(populate_by_name=True)


class VentaCreate(BaseModel):
    fecha: datetime = Field(..., description="Fecha y hora de la transacción")
    metodo_pago: str = Field(..., alias="metodoPago", description="Método utilizado para el cobro")
    monto_recibido: float = Field(..., alias="montoRecibido", ge=0, description="Dinero entregado por el comprador")
    vuelto: float = Field(..., ge=0, description="Diferencia entregada como cambio")
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

