# src/api/routes/ventaEndpoint.py
from fastapi import APIRouter, Depends, status, Response
from asyncpg import Connection

from core.session import get_db
from schemas.ventaSchema import VentaCreate, VentaResponse
from services import ventaServices
from utils.pdf_generator import resolver_comprobante_pdf

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

@router.get("/{venta_id}/imprimir", tags=["Operaciones - Ventas"])
async def imprimir_comprobante_venta(venta_id: int, conn: Connection = Depends(get_db)):
    """
    Busca los datos consolidados de una venta y devuelve el documento PDF 
    correspondiente (Ticket, Factura A o B) según se guardó en la transacción.
    """
    # 1. Recuperar cabecera operativa con los nuevos datos fiscales
    venta = await conn.fetchrow("""
        SELECT 
            v.id, v.fecha, v.total, v.tipo_comprobante, v.nro_comprobante,
            v.cliente_nombre, v.cliente_identificacion, v.cliente_condicion_iva,
            v.subtotal_neto, v.iva_21,
            a.descripcion as metodo_pago
        FROM ventas v
        JOIN asientos a ON v.asiento_id = a.id
        WHERE v.id = $1;
    """, venta_id)
    
    if not venta:
        return Response(status_code=status.HTTP_404_NOT_FOUND, content="La venta solicitada no existe.")

    # 2. Recuperar el desglose de ítems comercializados
    items = await conn.fetch("""
        SELECT p.nombre, vd.cantidad, vd.precio_unitario 
        FROM ventas_detalle vd
        JOIN producto p ON vd.producto_id = p.id
        WHERE vd.venta_id = $1;
    """, venta_id)

    # --- PARSEO DE DATOS (Solución al error Decimal vs Float) ---
    venta_dict = dict(venta)
    # Limpiamos el texto del método de pago extraído de la descripción del asiento contable
    venta_dict["metodo_pago"] = "Efectivo" if "Efectivo" in venta_dict["metodo_pago"] else "Transferencia"
    
    # Convertimos los valores Decimal de PostgreSQL a Float nativo de Python para que Jinja2 pueda operar
    if venta_dict["total"] is not None:
        venta_dict["total"] = float(venta_dict["total"])
    if venta_dict["subtotal_neto"] is not None:
        venta_dict["subtotal_neto"] = float(venta_dict["subtotal_neto"])
    if venta_dict["iva_21"] is not None:
        venta_dict["iva_21"] = float(venta_dict["iva_21"])

    items_list = []
    for item in items:
        item_dict = dict(item)
        if item_dict["precio_unitario"] is not None:
            # Convertimos el precio unitario a float
            item_dict["precio_unitario"] = float(item_dict["precio_unitario"])
        items_list.append(item_dict)
    # -------------------------------------------------------------

    # 3. Compilar el buffer binario del PDF
    pdf_content = resolver_comprobante_pdf(venta_dict, items_list)

    # 4. Retornar flujo de bytes application/pdf
    nombre_archivo = f"{venta_dict['tipo_comprobante'].replace(' ', '_')}_{venta_id}.pdf"
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={nombre_archivo}"
        }
    )