# src/schemas/productoSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150)
    tipo: str = Field(..., min_length=2, max_length=50)
    precio: float = Field(..., ge=0)
    costo: float = Field(0.0, ge=0)
    stock: int = Field(0, ge=0)
    stock_minimo: int = Field(5, ge=0)


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    tipo: Optional[str] = Field(None, min_length=2, max_length=50)
    precio: Optional[float] = Field(None, ge=0)
    costo: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)


class ProductoResponse(ProductoBase):
    id: int

    model_config = ConfigDict(from_attributes=True)
