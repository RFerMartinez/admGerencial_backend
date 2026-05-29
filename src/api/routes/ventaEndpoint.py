# src/api/routes/ventaEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection

from core.session import get_db
from schemas.ventaSchema import VentaCreate, VentaResponse
from services import ventaServices

router = APIRouter(prefix="/ventas", tags=["Operaciones - Ventas"])

@router.post("/", response_model=VentaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_venta(venta_data: VentaCreate, conn: Connection = Depends(get_db)):
    """
    Procesa una nueva venta de mostrador.
    
    Esta operación es transaccional (ACID). Automáticamente:
    1. Verifica el stock.
    2. Genera la cabecera del asiento contable.
    3. Guarda la venta y sus detalles.
    4. Descuenta el inventario.
    5. Genera la partida doble (Caja, Ventas, CMV, Mercaderías).
    """
    resultado = await ventaServices.procesar_venta(conn, venta_data)
    return resultado

