from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date


class CierreCreate(BaseModel):
    periodo: str = Field(..., pattern=r'^\d{4}-(0[1-9]|1[0-2])$')
    observaciones: Optional[str] = Field(None, max_length=255)


class CuentaCierreDetalle(BaseModel):
    cuenta_id: int
    cuenta_codigo: str
    cuenta_nombre: str
    saldo: float


class CierrePreview(BaseModel):
    periodo: str
    ingresos: List[CuentaCierreDetalle]
    egresos: List[CuentaCierreDetalle]
    total_ingresos: float
    total_egresos: float
    resultado: float


class CierreResponse(BaseModel):
    id: int
    periodo: str
    fecha_cierre: date
    asiento_id: int
    total_ingresos: float
    total_egresos: float
    resultado: float
    observaciones: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CierreListItem(BaseModel):
    id: int
    periodo: str
    fecha_cierre: date
    total_ingresos: float
    total_egresos: float
    resultado: float
    observaciones: Optional[str] = None
