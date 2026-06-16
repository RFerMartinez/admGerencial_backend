# src/api/routes/documentoEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from schemas.documentoSchema import DocumentoListResponse, NotaVentaCreate, NotaCompraCreate, NotaResponse
from services import documentoServices

router = APIRouter(prefix="/documentos", tags=["Gestión Documental Contable"])

@router.get("/", response_model=List[DocumentoListResponse], status_code=status.HTTP_200_OK)
async def listar_documentos_universales(conn: Connection = Depends(get_db)):
    """
    Obtiene el historial centralizado de documentos contables.
    Agrupa en memoria ventas, compras y notas de ajuste con sus respectivos detalles.
    """
    return await documentoServices.obtener_documentos(conn)

@router.post("/notas-venta", response_model=NotaResponse, status_code=status.HTTP_201_CREATED)
async def emitir_nota_venta(nota_data: NotaVentaCreate, conn: Connection = Depends(get_db)):
    """
    Procesa una Nota de Crédito o Débito sobre una factura de Venta.
    Reajusta saldos contables e impacta automáticamente en el inventario.
    """
    return await documentoServices.procesar_nota_venta(conn, nota_data)

@router.post("/notas-compra", response_model=NotaResponse, status_code=status.HTTP_201_CREATED)
async def registrar_nota_compra(nota_data: NotaCompraCreate, conn: Connection = Depends(get_db)):
    """
    Registra una Nota de Crédito o Débito emitida por un Proveedor.
    Requiere ingresar el Nro. de Comprobante físico y reajusta saldos pasivos.
    """
    return await documentoServices.procesar_nota_compra(conn, nota_data)

