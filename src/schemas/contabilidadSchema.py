# src/schemas/contabilidadSchema.py
from pydantic import BaseModel, Field
from typing import List, Literal, Union, Optional
from datetime import datetime, date

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

class MovimientoMayor(BaseModel):
    fecha: Union[datetime, date] = Field(..., description="Fecha del asiento")
    asiento_id: int = Field(..., description="ID del asiento asociado")
    descripcion: str = Field(..., description="Glosa o concepto del movimiento")
    debe: float = Field(..., description="Importe debitado")
    haber: float = Field(..., description="Importe acreditado")
    saldo_acumulado: float = Field(..., description="Saldo de corrida acumulado hasta este renglón")

class SaldoFinal(BaseModel):
    tipo: Literal["Deudor", "Acreedor", "Saldada"] = Field(..., description="Clasificación contable del saldo")
    valor: float = Field(..., description="Valor absoluto neto del saldo")

class CuentaLibroMayor(BaseModel):
    cuenta_id: int = Field(..., description="ID interno de la cuenta")
    cuenta_codigo: str = Field(..., description="Código de la cuenta")
    cuenta_nombre: str = Field(..., description="Nombre descriptivo de la cuenta")
    movimientos: List[MovimientoMayor] = Field(..., description="Listado cronológico de movimientos")
    saldo_final: SaldoFinal = Field(..., description="Estructura detallada del saldo final de la cuenta")

# --- NUEVOS ESQUEMAS PARA ASIENTOS MANUALES ---
class AsientoManualDetalle(BaseModel):
    cuenta_id: int = Field(..., description="ID de la cuenta contable")
    debe: float = Field(0.0, ge=0, description="Monto al Debe")
    haber: float = Field(0.0, ge=0, description="Monto al Haber")

class AsientoManualCreate(BaseModel):
    fecha: date = Field(..., description="Fecha del asiento")
    descripcion: str = Field(..., min_length=3, description="Concepto del asiento manual")
    detalles: List[AsientoManualDetalle] = Field(..., description="Renglones del asiento")
    
    # --- CAMPOS TOLERANTES PARA EL FRONTEND ---
    # Permitimos que el front envíe estos datos sin que FastAPI arroje error 422.
    # El servicio los ignorará al hacer el INSERT.
    total: Optional[float] = None
    total_debe: Optional[float] = None
    total_haber: Optional[float] = None