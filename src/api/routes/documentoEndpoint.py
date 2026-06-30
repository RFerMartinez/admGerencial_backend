# src/api/routes/documentoEndpoint.py
from fastapi import APIRouter, Depends, status, Response
from asyncpg import Connection
from typing import List

from core.session import get_db
from schemas.documentoSchema import DocumentoListResponse, NotaVentaCreate, NotaCompraCreate, NotaResponse
from services import documentoServices
from utils.pdf_generator import resolver_nota_pdf

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

@router.get("/{doc_id}/imprimir")
async def imprimir_nota(doc_id: int, conn: Connection = Depends(get_db)):
    """
    Genera el PDF de una Nota de Crédito/Débito emitida sobre una venta.
    No aplica a notas registradas sobre compras a proveedores.
    """
    nota_data = await documentoServices.obtener_nota_para_imprimir(conn, doc_id)
    pdf_content = resolver_nota_pdf(nota_data)
    nombre_archivo = f"{nota_data['tipo_comprobante'].replace(' ', '_')}_{doc_id}.pdf"
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={nombre_archivo}"}
    )

