from pydantic import BaseModel, Field


class CuentaSistemaItem(BaseModel):
    rol: str
    cuenta_id: int
    cuenta_nombre: str
    cuenta_codigo: str


class CuentaSistemaUpdate(BaseModel):
    cuenta_id: int = Field(..., gt=0)
