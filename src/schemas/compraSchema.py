# src/schemas/compraSchema.py
from pydantic import BaseModel, Field, ConfigDict, model_validator
from typing import List, Literal, Optional
from datetime import date

TipoComprobante = Literal["Factura A", "Factura B", "Factura C", "Ticket", "Cuenta Corriente"]
MetodoPago = Literal["Efectivo", "Transferencia", "Tarjeta"]

class CompraDetalle(BaseModel):
    producto_id: int = Field(..., description="ID del producto comprado")
    cantidad: int = Field(..., gt=0, description="Cantidad adquirida")
    costo_unitario: float = Field(..., ge=0, description="Costo al que nos vendió el proveedor")

class CompraCreate(BaseModel):
    fecha: date = Field(..., description="Fecha del comprobante")
    tipo_comprobante: TipoComprobante = Field(..., description="Documento que respalda la compra")
    total: float = Field(..., gt=0, description="Total facturado")
    detalles: List[CompraDetalle] = Field(..., min_length=1, description="Lista de productos comprados")
    
    metodo_pago: Optional[MetodoPago] = Field(None, description="Requerido si es Factura")
    nro_comprobante: Optional[str] = Field(default="S/N", max_length=50, description="Requerido si es Factura")
    cuenta_proveedor_id: Optional[int] = Field(None, description="ID de la cuenta contable (Requerido si es Cuenta Corriente)") 

    @model_validator(mode='after')
    def validar_campos_condicionales(self):
        if self.tipo_comprobante == "Cuenta Corriente":
            if self.cuenta_proveedor_id is None:
                raise ValueError("El campo 'cuenta_proveedor_id' es obligatorio cuando se compra en Cuenta Corriente.")
            self.metodo_pago = None 
            self.nro_comprobante = "S/N"
        else:
            if self.metodo_pago is None:
                raise ValueError(f"El campo 'metodo_pago' es obligatorio para {self.tipo_comprobante}.")
            if not self.nro_comprobante:
                self.nro_comprobante = "S/N"
                
        return self

    model_config = ConfigDict(populate_by_name=True)

class CompraResponse(BaseModel):
    id: int
    fecha: date
    total: float
    asiento_id: int
    tipo_comprobante: str 
    nro_comprobante: str
    mensaje: str = "Compra registrada y contabilizada exitosamente."

    model_config = ConfigDict(from_attributes=True)

