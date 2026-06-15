# src/services/documentoServices.py
import asyncpg
import random
from asyncpg import Connection
from schemas.documentoSchema import NotaVentaCreate, NotaCompraCreate
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


async def procesar_nota_venta(conn: Connection, nota_data: NotaVentaCreate) -> dict:
    async with conn.transaction():
        # 1. Validar Padre
        padre = await conn.fetchrow("""
            SELECT dc.id, v.asiento_id 
            FROM documentos_contables dc
            LEFT JOIN ventas v ON dc.venta_id = v.id
            WHERE dc.id = $1
        """, nota_data.comprobante_padre_id)
        
        if not padre:
            raise NotFoundException("Comprobante original no encontrado.")
            
        is_credito = "crédito" in nota_data.tipo_comprobante.lower() or "credito" in nota_data.tipo_comprobante.lower()
        nro_comprobante = f"0001-{random.randint(10000000, 99999999)}"

        # 2. Persistencia Documental
        doc_id = await conn.fetchval("""
            INSERT INTO documentos_contables (
                tipo_comprobante, nro_comprobante, fecha_emision, total, comprobante_padre_id
            ) VALUES ($1, $2, CURRENT_DATE, $3, $4) RETURNING id;
        """, nota_data.tipo_comprobante, nro_comprobante, nota_data.total_modificado, nota_data.comprobante_padre_id)

        # 3. Control de Inventario
        costo_total_modificado = 0.0
        for item in nota_data.items_afectados:
            if is_credito: # Vuelve al kiosco
                await conn.execute("UPDATE producto SET stock = stock + $1 WHERE id = $2", item.cantidad, item.producto_id)
            else: # Sale del kiosco (recargo físico)
                await conn.execute("UPDATE producto SET stock = stock - $1 WHERE id = $2", item.cantidad, item.producto_id)
                
            costo = await conn.fetchval("SELECT costo FROM producto WHERE id = $1", item.producto_id)
            costo_total_modificado += float(costo) * item.cantidad

        # 4. Contabilidad Automatizada
        # Inferimos cuenta de cobro del asiento original
        cuenta_cobro_id = None
        if padre['asiento_id']:
            cuenta_cobro_id = await conn.fetchval("""
                SELECT ad.cuenta_id FROM asientos_detalle ad
                JOIN cuentas c ON ad.cuenta_id = c.id
                WHERE ad.asiento_id = $1 AND c.codigo IN ('110001', '110003') LIMIT 1
            """, padre['asiento_id'])
            
        if not cuenta_cobro_id:
            cuenta_cobro_id = await conn.fetchval("SELECT id FROM cuentas WHERE codigo = '110001'")

        c_ventas = await conn.fetchval("SELECT id FROM cuentas WHERE codigo = '410001'")
        c_merca = await conn.fetchval("SELECT id FROM cuentas WHERE codigo = '140002'")
        c_cmv = await conn.fetchval("SELECT id FROM cuentas WHERE codigo = '510007'")

        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES (CURRENT_DATE, $1) RETURNING id;",
            f"{nota_data.tipo_comprobante} - Ref. {nota_data.comprobante_padre_id}: {nota_data.motivo}"
        )

        renglones = []
        if is_credito:
            # Reversión de Ganancia e Ingreso (Debe: Ventas | Haber: Caja/Banco)
            renglones.extend([
                (asiento_id, c_ventas, nota_data.total_modificado, 0.00),
                (asiento_id, cuenta_cobro_id, 0.00, nota_data.total_modificado)
            ])
            if costo_total_modificado > 0:
                renglones.extend([
                    (asiento_id, c_merca, costo_total_modificado, 0.00),
                    (asiento_id, c_cmv, 0.00, costo_total_modificado)
                ])
        else:
            # Aumento de Ganancia e Ingreso (Debe: Caja/Banco | Haber: Ventas)
            renglones.extend([
                (asiento_id, cuenta_cobro_id, nota_data.total_modificado, 0.00),
                (asiento_id, c_ventas, 0.00, nota_data.total_modificado)
            ])
            if costo_total_modificado > 0:
                renglones.extend([
                    (asiento_id, c_cmv, costo_total_modificado, 0.00),
                    (asiento_id, c_merca, 0.00, costo_total_modificado)
                ])

        await conn.executemany(
            "INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) VALUES ($1, $2, $3, $4)",
            renglones
        )

        return {"id": doc_id, "asiento_id": asiento_id, "nro_comprobante": nro_comprobante, "mensaje": "Nota de ajuste sobre Venta registrada exitosamente."}


async def procesar_nota_compra(conn: Connection, nota_data: NotaCompraCreate) -> dict:
    async with conn.transaction():
        # 1. Validar Padre
        padre = await conn.fetchrow("""
            SELECT dc.id, cm.asiento_id 
            FROM documentos_contables dc
            LEFT JOIN compras_mercaderia cm ON dc.compra_id = cm.id
            WHERE dc.id = $1
        """, nota_data.comprobante_padre_id)
        
        if not padre:
            raise NotFoundException("Comprobante original no encontrado.")
            
        is_credito = "crédito" in nota_data.tipo_comprobante.lower() or "credito" in nota_data.tipo_comprobante.lower()

        # 2. Persistencia Documental
        doc_id = await conn.fetchval("""
            INSERT INTO documentos_contables (
                tipo_comprobante, nro_comprobante, fecha_emision, total, comprobante_padre_id
            ) VALUES ($1, $2, CURRENT_DATE, $3, $4) RETURNING id;
        """, nota_data.tipo_comprobante, nota_data.nro_comprobante_recibido, nota_data.total_modificado, nota_data.comprobante_padre_id)

        # 3. Control de Inventario
        for item in nota_data.items_afectados:
            if is_credito: # Devolución de mercadería al proveedor
                await conn.execute("UPDATE producto SET stock = stock - $1 WHERE id = $2", item.cantidad, item.producto_id)
            else: # Nos mandan más mercadería
                await conn.execute("UPDATE producto SET stock = stock + $1 WHERE id = $2", item.cantidad, item.producto_id)

        # 4. Contabilidad Automatizada
        cuenta_pago_id = None
        if padre['asiento_id']:
            cuenta_pago_id = await conn.fetchval("""
                SELECT ad.cuenta_id FROM asientos_detalle ad
                JOIN cuentas c ON ad.cuenta_id = c.id
                WHERE ad.asiento_id = $1 AND (c.tipo = 'Pasivo' OR c.codigo IN ('110001', '110003')) LIMIT 1
            """, padre['asiento_id'])
            
        if not cuenta_pago_id:
            cuenta_pago_id = await conn.fetchval("SELECT id FROM cuentas WHERE codigo = '110001'")

        c_merca = await conn.fetchval("SELECT id FROM cuentas WHERE codigo = '140002'")

        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES (CURRENT_DATE, $1) RETURNING id;",
            f"{nota_data.tipo_comprobante} - Ref. {nota_data.comprobante_padre_id}: {nota_data.motivo}"
        )

        renglones = []
        if is_credito:
            # Disminuye la deuda / Proveedor nos devuelve dinero (Debe) -> Disminuye Mercaderías (Haber)
            renglones.extend([
                (asiento_id, cuenta_pago_id, nota_data.total_modificado, 0.00),
                (asiento_id, c_merca, 0.00, nota_data.total_modificado)
            ])
        else:
            # Aumenta Mercaderías (Debe) -> Aumenta Deuda a Proveedor (Haber)
            renglones.extend([
                (asiento_id, c_merca, nota_data.total_modificado, 0.00),
                (asiento_id, cuenta_pago_id, 0.00, nota_data.total_modificado)
            ])

        await conn.executemany(
            "INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) VALUES ($1, $2, $3, $4)",
            renglones
        )

        return {"id": doc_id, "asiento_id": asiento_id, "nro_comprobante": nota_data.nro_comprobante_recibido, "mensaje": "Nota de ajuste sobre Compra registrada exitosamente."}
    
    