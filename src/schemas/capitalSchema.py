# src/schemas/capitalSchema.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import date

class CapitalInicialCreate(BaseModel):
    fecha: date = Field(..., description="Fecha de inicio de actividades")
    monto_caja: float = Field(0.0, ge=0, description="Saldo inicial físico (Efectivo)")
    monto_banco: float = Field(0.0, ge=0, description="Saldo inicial en cuenta bancaria")

class CapitalResponse(BaseModel):
    asiento_id: int
    total_capital: float
    mensaje: str = "Capital inicial registrado y contabilizado exitosamente."

    model_config = ConfigDict(from_attributes=True)

