# src/schemas/compraSchema.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Optional
from datetime import date


class CompraDetalle(BaseModel):
    producto_id: int = Field(...)
    cantidad: int = Field(..., gt=0)
    costo_unitario: float = Field(..., ge=0)


class CompraCreate(BaseModel):
    fecha: date = Field(...)
    tipo_comprobante: str = Field(...)
    nro_comprobante: str = Field(..., max_length=50)
    total: float = Field(..., gt=0)
    detalles: List[CompraDetalle] = Field(..., min_length=1)

    metodo_pago: Optional[str] = Field(None)
    proveedor_id: Optional[int] = Field(None)

    @model_validator(mode='after')
    def validar_campos_condicionales(self):
        if self.proveedor_id is not None:
            self.metodo_pago = None
        elif self.metodo_pago is None:
            raise ValueError("Debe indicar 'metodo_pago' o 'proveedor_id'.")
        return self

    model_config = ConfigDict(populate_by_name=True)


class CompraResponse(BaseModel):
    id: int
    fecha: date
    total: float
    asiento_id: int
    tipo_comprobante: str
    nro_comprobante: str
    mensaje: str = "Compra registrada y contabilizada exitosamente."

    model_config = ConfigDict(from_attributes=True)
