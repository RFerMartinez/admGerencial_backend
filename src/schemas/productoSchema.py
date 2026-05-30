# src/schemas/productoSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional

class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=150, description="Nombre del producto")
    tipo: str = Field(..., min_length=2, max_length=50, description="Categoría o tipo (Debe existir en categorias)")
    precio: float = Field(..., ge=0, description="Precio de venta mayor o igual a 0")
    costo: float = Field(0.0, ge=0, description="Costo de adquisición mayor o igual a 0")
    stock: int = Field(0, ge=0, description="Cantidad en inventario")

class ProductoCreate(ProductoBase):
    pass

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=150)
    tipo: Optional[str] = Field(None, min_length=2, max_length=50)
    precio: Optional[float] = Field(None, ge=0)
    costo: Optional[float] = Field(None, ge=0)
    stock: Optional[int] = Field(None, ge=0)

class ProductoResponse(ProductoBase):
    id: int
    
    model_config = ConfigDict(from_attributes=True)
