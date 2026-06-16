# src/schemas/contabilidadSchema.py
from pydantic import BaseModel, Field
from typing import List, Literal
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

class MovimientoMayor(BaseModel):
    fecha: Union[datetime, date] = Field(..., description="Fecha del asiento")
    asiento_id: int = Field(..., description="ID del asiento asociado")
    descripcion: str = Field(..., description="Glosa o concepto del movimiento")
    debe: float = Field(..., description="Importe debitado")
    haber: float = Field(..., description="Importe acreditado")
    saldo_acumulado: float = Field(..., description="Saldo de corrida acumulado hasta este renglón")

class CuentaLibroMayor(BaseModel):
    cuenta_id: int = Field(..., description="ID interno de la cuenta")
    cuenta_codigo: str = Field(..., description="Código de 6 dígitos de la cuenta")
    cuenta_nombre: str = Field(..., description="Nombre descriptivo de la cuenta")
    saldo_final: float = Field(..., description="Saldo neto final de la cuenta")
    movimientos: List[MovimientoMayor] = Field(..., description="Listado cronológico de movimientos")

class SaldoFinal(BaseModel):
    tipo: Literal["Deudor", "Acreedor", "Saldada"] = Field(..., description="Clasificación contable del saldo")
    valor: float = Field(..., description="Valor absoluto neto del saldo")

class CuentaLibroMayor(BaseModel):
    cuenta_id: int = Field(..., description="ID interno de la cuenta")
    cuenta_codigo: str = Field(..., description="Código de la cuenta")
    cuenta_nombre: str = Field(..., description="Nombre descriptivo de la cuenta")
    movimientos: List[MovimientoMayor] = Field(..., description="Listado cronológico de movimientos")
    saldo_final: SaldoFinal = Field(..., description="Estructura detallada del saldo final de la cuenta")

