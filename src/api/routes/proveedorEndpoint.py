# src/api/routes/proveedorEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from schemas.proveedorSchema import DeudaProveedorResponse, PagoProveedorCreate, PagoProveedorResponse, MovimientoProveedor
from services import proveedorServices

router = APIRouter(prefix="/proveedores", tags=["Gestión de Proveedores"])

@router.get("/deudas", response_model=List[DeudaProveedorResponse], status_code=status.HTTP_200_OK)
async def listar_deudas_activas(conn: Connection = Depends(get_db)):
    """
    Obtiene la lista de proveedores a los que se les debe dinero.
    Calcula dinámicamente el saldo en base al Libro Diario (Pasivo > 0).
    """
    return await proveedorServices.obtener_deudas_activas(conn)

@router.get("/{proveedor_id}/movimientos", response_model=List[MovimientoProveedor], status_code=status.HTTP_200_OK)
async def listar_movimientos_proveedor(proveedor_id: int, conn: Connection = Depends(get_db)):
    """
    Detalle de movimientos de cuenta corriente de un proveedor: compras y gastos
    a Cuenta Corriente (generan deuda) y pagos registrados (la reducen), con saldo acumulado.
    """
    return await proveedorServices.obtener_movimientos(conn, proveedor_id)

@router.post("/pagos", response_model=PagoProveedorResponse, status_code=status.HTTP_201_CREATED)
async def pagar_proveedor(pago_data: PagoProveedorCreate, conn: Connection = Depends(get_db)):
    """
    Registra un pago a un proveedor.
    Genera el asiento contable (Partida Doble) debitando de la cuenta del proveedor
    y acreditando la salida de Caja/Banco.
    """
    resultado = await proveedorServices.registrar_pago(conn, pago_data)
    return resultado