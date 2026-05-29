from pydantic import BaseModel, Field, ConfigDict

class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50, description="Nombre único de la categoría")

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=50, description="Nuevo nombre de la categoría")

class CategoriaResponse(CategoriaBase):
    model_config = ConfigDict(from_attributes=True)

