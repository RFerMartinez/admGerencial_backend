from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import Optional, Literal
from datetime import date


class GastoCreate(BaseModel):
    fecha: date
    descripcion: str = Field(..., min_length=1, max_length=255)
    cuenta_debe_id: int = Field(..., gt=0)
    monto: float = Field(..., gt=0)
    tipo_comprobante: str = Field(..., min_length=1, max_length=50)
    nro_comprobante: str = Field(default="S/N", max_length=50)
    metodo_pago: Optional[Literal["Efectivo", "Transferencia"]] = None
    proveedor_id: Optional[int] = None

    @model_validator(mode='after')
    def validar_pago(self):
        if self.proveedor_id is not None:
            self.metodo_pago = None
        elif self.metodo_pago is None:
            raise ValueError("Debe indicar 'metodo_pago' o 'proveedor_id'.")
        return self

    model_config = ConfigDict(populate_by_name=True)


class GastoResponse(BaseModel):
    id: int
    fecha: date
    monto: float
    asiento_id: int
    tipo_comprobante: str
    nro_comprobante: str
    mensaje: str = "Gasto registrado y contabilizado exitosamente."

    model_config = ConfigDict(from_attributes=True)
