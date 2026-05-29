# src/schemas/cuentaSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal

# Definimos los tipos permitidos según el CHECK constraint de la DB
TipoCuenta = Literal['Activo', 'Pasivo', 'Patrimonio Neto', 'Ingreso', 'Egreso']

class CuentaBase(BaseModel):
    codigo: Optional[str] = Field(None, max_length=20, description="Código jerárquico de la cuenta (Ej: 1.1.1.01)")
    nombre: str = Field(..., min_length=2, max_length=100, description="Nombre descriptivo de la cuenta")
    tipo: TipoCuenta = Field(..., description="Tipo de cuenta contable según la partida doble")

class CuentaCreate(CuentaBase):
    pass

class CuentaUpdate(BaseModel):
    codigo: Optional[str] = Field(None, max_length=20)
    nombre: Optional[str] = Field(None, min_length=2, max_length=100)
    tipo: Optional[TipoCuenta] = Field(None)

class CuentaResponse(CuentaBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)

# Formato de respuesta envuelto solicitado para el listado masivo
class CuentaListResponse(BaseModel):
    status: str
    data: List[CuentaResponse]

