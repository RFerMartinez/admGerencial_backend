# src/schemas/contabilidadSchema.py
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime, date
from typing import Union

class DetalleAsiento(BaseModel):
    cuenta_codigo: str = Field(..., description="Código jerárquico de la cuenta")
    cuenta_nombre: str = Field(..., description="Nombre de la cuenta contable")
    debe: float = Field(..., description="Monto debitado")
    haber: float = Field(..., description="Monto acreditado")

class AsientoDiario(BaseModel):
    nro_asiento: int = Field(..., description="ID del asiento contable")
    fecha: Union[datetime, date] = Field(..., description="Fecha de registro")
    descripcion: str = Field(..., description="Descripción o glosa del asiento")
    detalles: List[DetalleAsiento] = Field(..., description="Renglones del asiento por partida doble")
    total_debe: float = Field(..., description="Suma total de la columna Debe del asiento")
    total_haber: float = Field(..., description="Suma total de la columna Haber del asiento")

