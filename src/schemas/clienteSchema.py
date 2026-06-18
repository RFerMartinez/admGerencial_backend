from pydantic import BaseModel, Field
from typing import Optional

class ClienteBase(BaseModel):
    razon_social: str = Field(..., max_length=255)
    domicilio_fiscal: Optional[str] = None
    condicion_iva: str = Field(..., max_length=50)

class ClienteCreate(ClienteBase):
    cuit: str = Field(..., max_length=20, description="CUIT/CUIL del cliente, será la PK")

class ClienteResponse(ClienteCreate):
    pass