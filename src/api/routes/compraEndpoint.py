# src/api/routes/compraEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection

from core.session import get_db
from schemas.compraSchema import CompraCreate, CompraResponse
from services import compraServices

router = APIRouter(prefix="/compras", tags=["Operaciones - Compras"])

@router.post("/", response_model=CompraResponse, status_code=status.HTTP_201_CREATED)
async def registrar_compra(compra_data: CompraCreate, conn: Connection = Depends(get_db)):
    """
    Registra una factura de compra a proveedores.
    
    Esta operación ejecuta automáticamente los siguientes pasos en una sola transacción:
    1. Registra el asiento contable (Mercaderías a Caja/Banco).
    2. Guarda el comprobante operativo.
    3. Registra el detalle de los productos adquiridos.
    4. Aumenta el stock de los productos.
    5. Actualiza el COSTO de los productos en base al precio pagado al proveedor.
    """
    resultado = await compraServices.procesar_compra(conn, compra_data)
    return resultado

