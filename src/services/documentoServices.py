# src/services/documentoServices.py
import asyncpg
import random
from asyncpg import Connection
from schemas.documentoSchema import NotaPayload, NotaVentaCreate, NotaCompraCreate
from utils.exceptions import NotFoundException, DatabaseException

async def obtener_documentos(conn: Connection) -> list[dict]:
    query = """
        SELECT 
            dc.id,
            CASE 
                WHEN dc.venta_id IS NOT NULL THEN 'Venta'
                WHEN dc.compra_id IS NOT NULL THEN 'Compra'
                ELSE 'Ajuste/Nota' 
            END as tipo_operacion,
            dc.fecha_emision,
            dc.tipo_comprobante,
            dc.nro_comprobante,
            COALESCE(dc.cliente_proveedor_nombre, 'Consumidor Final') as entidad_nombre,
            dc.total,
            p.id as producto_id,
            p.nombre as producto_nombre,
            COALESCE(vd.cantidad, cd.cantidad) as cantidad,
            COALESCE(vd.precio_unitario, cd.costo_unitario) as precio_unitario
        FROM documentos_contables dc
        LEFT JOIN ventas_detalle vd ON dc.venta_id = vd.venta_id
        LEFT JOIN compras_detalle cd ON dc.compra_id = cd.compra_id
        LEFT JOIN producto p ON p.id = vd.producto_id OR p.id = cd.producto_id
        ORDER BY dc.fecha_emision DESC, dc.id DESC;
    """
    records = await conn.fetch(query)
    
    # Estructuramos en memoria agolpando los items por documento
    documentos_agrupados = {}
    for row in records:
        doc_id = row['id']
        if doc_id not in documentos_agrupados:
            documentos_agrupados[doc_id] = {
                "id": doc_id,
                "tipo_operacion": row['tipo_operacion'],
                "fecha_emision": row['fecha_emision'],
                "tipo_comprobante": row['tipo_comprobante'],
                "nro_comprobante": row['nro_comprobante'],
                "entidad_nombre": row['entidad_nombre'],
                "total": float(row['total']),
                "items_originales": []
            }
            
        if row['producto_id'] is not None:
            documentos_agrupados[doc_id]["items_originales"].append({
                "producto_id": row['producto_id'],
                "nombre": row['producto_nombre'],
                "cantidad": row['cantidad'],
                "precio_unitario": float(row['precio_unitario'])
            })
            
    return list(documentos_agrupados.values())


async def procesar_nota_venta(conn: asyncpg.Connection, payload: NotaPayload) -> None:
    # Encapsulamos la lógica en una transacción[cite: 1]
    async with conn.transaction():
        
        # 1. Contabilidad Corta: El asiento SOLO debe ajustar la Venta (Caja vs Ventas) por el total_modificado[cite: 1]
        asiento_id = await conn.fetchval(
            """
            INSERT INTO asientos_contables (descripcion, monto) 
            VALUES ($1, $2) RETURNING id
            """,
            f"Nota de Venta - {payload.motivo}", payload.total_modificado
        )
        await conn.execute(
            """
            INSERT INTO renglones_contables (asiento_id, cuenta_debe, cuenta_haber, monto) 
            VALUES ($1, 'Ventas', 'Caja', $2)
            """,
            asiento_id, payload.total_modificado
        )

        # 2. Procesamiento de items
        for item in payload.items_afectados:
            if item.cantidad > 0:
                # Ajuste Físico: Suma stock (la mercadería volvió al local)[cite: 1]
                await conn.execute(
                    "UPDATE producto SET stock = stock + $1 WHERE id = $2",
                    item.cantidad, item.producto_id
                )
                
                # Contabilidad Completa: Revertir CMV proporcional a unidades devueltas[cite: 1]
                costo_unitario = await conn.fetchval(
                    "SELECT costo FROM producto WHERE id = $1", 
                    item.producto_id
                )
                
                if costo_unitario:
                    cmv_revertido = costo_unitario * item.cantidad
                    await conn.execute(
                        """
                        INSERT INTO renglones_contables (asiento_id, cuenta_debe, cuenta_haber, monto) 
                        VALUES ($1, 'Mercaderías', 'CMV', $2)
                        """,
                        asiento_id, cmv_revertido
                    )
                    
            elif item.cantidad == 0 and item.nuevo_precio is not None:
                # Ajuste Financiero: No toca stock, actualiza precio en catálogo. NO genera CMV[cite: 1]
                await conn.execute(
                    "UPDATE producto SET precio = $1 WHERE id = $2",
                    item.nuevo_precio, item.producto_id
                )


async def procesar_nota_compra(conn: asyncpg.Connection, payload: NotaPayload) -> None:
    # Encapsulamos la lógica en una transacción[cite: 1]
    async with conn.transaction():
        
        # 1. Contabilidad de la Compra: Mueve la cuenta del Proveedor/Caja contra Mercaderías/Ajuste por total_modificado independientemente de si movió stock[cite: 1]
        asiento_id = await conn.fetchval(
            """
            INSERT INTO asientos_contables (descripcion, monto) 
            VALUES ($1, $2) RETURNING id
            """,
            f"Nota de Compra - {payload.motivo}", payload.total_modificado
        )
        await conn.execute(
            """
            INSERT INTO renglones_contables (asiento_id, cuenta_debe, cuenta_haber, monto) 
            VALUES ($1, 'Proveedores/Caja', 'Mercaderías/Ajuste', $2)
            """,
            asiento_id, payload.total_modificado
        )

        # 2. Procesamiento de items
        for item in payload.items_afectados:
            if item.cantidad > 0:
                # Ajuste Físico[cite: 1]
                if "Crédito" in payload.tipo_comprobante:
                    # Descuenta stock (el proveedor se llevó la mercadería fallada)[cite: 1]
                    await conn.execute(
                        "UPDATE producto SET stock = stock - $1 WHERE id = $2",
                        item.cantidad, item.producto_id
                    )
                elif "Débito" in payload.tipo_comprobante:
                    # Suma stock (el proveedor mandó cajas que faltaban)[cite: 1]
                    await conn.execute(
                        "UPDATE producto SET stock = stock + $1 WHERE id = $2",
                        item.cantidad, item.producto_id
                    )
            elif item.cantidad == 0 and item.nuevo_costo is not None:
                # Ajuste Financiero: No toca stock, actualiza costo en catálogo[cite: 1]
                await conn.execute(
                    "UPDATE producto SET costo = $1 WHERE id = $2",
                    item.nuevo_costo, item.producto_id
                )


async def procesar_nota_venta(conn: asyncpg.Connection, payload: NotaPayload) -> None:
    # Encapsulamos la lógica en una transacción[cite: 1]
    async with conn.transaction():
        
        # 1. Contabilidad Corta: El asiento SOLO debe ajustar la Venta (Caja vs Ventas) por el total_modificado[cite: 1]
        asiento_id = await conn.fetchval(
            """
            INSERT INTO asientos_contables (descripcion, monto) 
            VALUES ($1, $2) RETURNING id
            """,
            f"Nota de Venta - {payload.motivo}", payload.total_modificado
        )
        await conn.execute(
            """
            INSERT INTO renglones_contables (asiento_id, cuenta_debe, cuenta_haber, monto) 
            VALUES ($1, 'Ventas', 'Caja', $2)
            """,
            asiento_id, payload.total_modificado
        )

        # 2. Procesamiento de items
        for item in payload.items_afectados:
            if item.cantidad > 0:
                # Ajuste Físico: Suma stock (la mercadería volvió al local)[cite: 1]
                await conn.execute(
                    "UPDATE producto SET stock = stock + $1 WHERE id = $2",
                    item.cantidad, item.producto_id
                )
                
                # Contabilidad Completa: Revertir CMV proporcional a unidades devueltas[cite: 1]
                costo_unitario = await conn.fetchval(
                    "SELECT costo FROM producto WHERE id = $1", 
                    item.producto_id
                )
                
                if costo_unitario:
                    cmv_revertido = costo_unitario * item.cantidad
                    await conn.execute(
                        """
                        INSERT INTO renglones_contables (asiento_id, cuenta_debe, cuenta_haber, monto) 
                        VALUES ($1, 'Mercaderías', 'CMV', $2)
                        """,
                        asiento_id, cmv_revertido
                    )
                    
            elif item.cantidad == 0 and item.nuevo_precio is not None:
                # Ajuste Financiero: No toca stock, actualiza precio en catálogo. NO genera CMV[cite: 1]
                await conn.execute(
                    "UPDATE producto SET precio = $1 WHERE id = $2",
                    item.nuevo_precio, item.producto_id
                )   
