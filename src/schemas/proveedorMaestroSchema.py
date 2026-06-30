from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProveedorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    cuit: Optional[str] = Field(None, max_length=20)
    domicilio: Optional[str] = Field(None, max_length=255)
    telefono: Optional[str] = Field(None, max_length=50)


class ProveedorResponse(BaseModel):
    id: int
    nombre: str
    cuit: Optional[str] = None
    domicilio: Optional[str] = None
    telefono: Optional[str] = None
    activo: bool = True

    model_config = ConfigDict(from_attributes=True)


class ProveedorEstadoUpdate(BaseModel):
    activo: bool


class ProveedorConDeuda(BaseModel):
    id: int
    nombre: str
    cuit: Optional[str] = None
    saldo_pendiente: float
