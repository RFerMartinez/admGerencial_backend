# src/schemas/documentoSchema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import date


# --- GET: Listado Universal ---
class ItemOriginal(BaseModel):
    producto_id: int
    nombre: str
    cantidad: int
    precio_unitario: float


class PadreInfo(BaseModel):
    tipo_comprobante: str
    nro_comprobante: str
    fecha_emision: Optional[str] = None
    total: float = 0
    entidad: str = ''
    tipo_operacion: str = ''


class DocumentoListResponse(BaseModel):
    id: int
    tipo_operacion: str
    fecha_emision: date
    tipo_comprobante: str
    nro_comprobante: str
    entidad_nombre: str
    total: float
    venta_id: Optional[int] = None
    compra_id: Optional[int] = None
    gasto_id: Optional[int] = None
    comprobante_padre_id: Optional[int] = None
    cantidad_notas: int = 0
    items_originales: List[ItemOriginal] = []
    proveedor_nombre: Optional[str] = None
    proveedor_cuit: Optional[str] = None
    gasto_descripcion: Optional[str] = None
    gasto_cuenta_nombre: Optional[str] = None
    gasto_cuenta_codigo: Optional[str] = None
    padre_info: Optional[PadreInfo] = None
    nota_motivo: Optional[str] = None
    pago_monto: Optional[float] = None
    pago_asiento_id: Optional[int] = None
    pago_observaciones: Optional[str] = None
    pago_metodo_pago: Optional[str] = None


# --- POST: Notas de Crédito / Débito ---
class ItemAfectado(BaseModel):
    producto_id: int
    cantidad: int = Field(..., ge=0)
    precio_unitario: float = Field(..., ge=0)
    nuevo_costo: Optional[float] = None
    nuevo_precio: Optional[float] = None


class NotaVentaCreate(BaseModel):
    comprobante_padre_id: int
    tipo_comprobante: str
    motivo: str
    total_modificado: float = Field(..., gt=0)
    items_afectados: List[ItemAfectado] = []
    fecha: date = Field(..., description="Fecha de emisión de la nota (fecha local del usuario)")


class NotaCompraCreate(BaseModel):
    comprobante_padre_id: int
    tipo_comprobante: str
    nro_comprobante_recibido: str
    motivo: str
    total_modificado: float = Field(..., gt=0)
    items_afectados: List[ItemAfectado] = []
    fecha: date = Field(..., description="Fecha de emisión de la nota (fecha local del usuario)")


class NotaResponse(BaseModel):
    id: int
    asiento_id: int
    nro_comprobante: str
    mensaje: str

    model_config = ConfigDict(from_attributes=True)
