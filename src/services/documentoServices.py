# src/services/documentoServices.py
import random
from datetime import datetime
from asyncpg import Connection
from schemas.documentoSchema import NotaVentaCreate, NotaCompraCreate
from utils.exceptions import NotFoundException, DatabaseException, BadRequestException
from services.cuentaSistemaServices import resolver_cuentas_sistema


async def obtener_documentos(conn: Connection) -> list[dict]:
    query = """
        SELECT
            dc.id,
            COALESCE(dc.tipo_operacion,
                CASE
                    WHEN dc.venta_id IS NOT NULL THEN 'Venta'
                    WHEN dc.compra_id IS NOT NULL THEN 'Compra'
                    WHEN dc.gasto_id IS NOT NULL THEN 'Gasto'
                    ELSE 'Ajuste/Nota'
                END
            ) as tipo_operacion,
            dc.fecha_emision,
            dc.tipo_comprobante,
            dc.nro_comprobante,
            COALESCE(dc.entidad_nombre, dc.cliente_proveedor_nombre, '') as entidad_nombre,
            dc.total,
            dc.venta_id,
            dc.compra_id,
            dc.gasto_id,
            dc.comprobante_padre_id,
            -- Items de venta
            vd.producto_id as vd_producto_id,
            pv.nombre as vd_producto_nombre,
            vd.cantidad as vd_cantidad,
            vd.precio_unitario as vd_precio_unitario,
            -- Items de compra
            cd.producto_id as cd_producto_id,
            pc.nombre as cd_producto_nombre,
            cd.cantidad as cd_cantidad,
            cd.costo_unitario as cd_costo_unitario,
            -- Datos de gasto
            g.descripcion as gasto_descripcion,
            cg.nombre as gasto_cuenta_nombre,
            cg.codigo as gasto_cuenta_codigo,
            -- Proveedor (maestro)
            prov.nombre as proveedor_nombre,
            prov.cuit as proveedor_cuit,
            -- Datos del pago (tracking individual + asiento)
            pago.monto as pago_monto,
            pago.asiento_id as pago_asiento_id,
            pago_asiento.descripcion as pago_observaciones,
            pago_metodo.rol as pago_metodo_rol,
            -- Notas hijas
            (SELECT COUNT(*) FROM documentos_contables hijo WHERE hijo.comprobante_padre_id = dc.id) as cantidad_notas,
            -- Documento padre (para notas)
            padre.tipo_comprobante as padre_tipo_comprobante,
            padre.nro_comprobante as padre_nro_comprobante,
            padre.fecha_emision as padre_fecha_emision,
            padre.total as padre_total,
            COALESCE(padre.entidad_nombre, padre.cliente_proveedor_nombre, '') as padre_entidad,
            COALESCE(padre.tipo_operacion,
                CASE
                    WHEN padre.venta_id IS NOT NULL THEN 'Venta'
                    WHEN padre.compra_id IS NOT NULL THEN 'Compra'
                    ELSE ''
                END
            ) as padre_tipo_operacion,
            dc.motivo_nota
        FROM documentos_contables dc
        LEFT JOIN ventas_detalle vd ON dc.venta_id = vd.venta_id
        LEFT JOIN producto pv ON pv.id = vd.producto_id
        LEFT JOIN compras_detalle cd ON dc.compra_id = cd.compra_id
        LEFT JOIN producto pc ON pc.id = cd.producto_id
        LEFT JOIN gastos g ON dc.gasto_id = g.id
        LEFT JOIN cuentas cg ON g.cuenta_debe_id = cg.id
        LEFT JOIN compras_mercaderia cm ON dc.compra_id = cm.id
        LEFT JOIN pagos_proveedor pago ON dc.pago_id = pago.id
        LEFT JOIN proveedores prov ON cm.proveedor_id = prov.id OR g.proveedor_id = prov.id OR pago.proveedor_id = prov.id
        LEFT JOIN asientos pago_asiento ON pago.asiento_id = pago_asiento.id
        LEFT JOIN LATERAL (
            SELECT cs.rol FROM asientos_detalle ad
            JOIN cuentas_sistema cs ON cs.cuenta_id = ad.cuenta_id AND cs.rol IN ('CAJA', 'BANCO')
            WHERE ad.asiento_id = pago.asiento_id
            LIMIT 1
        ) pago_metodo ON pago.asiento_id IS NOT NULL
        LEFT JOIN documentos_contables padre ON dc.comprobante_padre_id = padre.id
        ORDER BY dc.fecha_emision DESC, dc.id DESC;
    """
    records = await conn.fetch(query)

    documentos_agrupados = {}
    for row in records:
        doc_id = row['id']
        if doc_id not in documentos_agrupados:
            doc = {
                "id": doc_id,
                "tipo_operacion": row['tipo_operacion'],
                "fecha_emision": row['fecha_emision'],
                "tipo_comprobante": row['tipo_comprobante'],
                "nro_comprobante": row['nro_comprobante'],
                "entidad_nombre": row['entidad_nombre'],
                "total": float(row['total']),
                "venta_id": row['venta_id'],
                "compra_id": row['compra_id'],
                "gasto_id": row['gasto_id'],
                "comprobante_padre_id": row['comprobante_padre_id'],
                "cantidad_notas": row['cantidad_notas'],
                "items_originales": [],
            }
            if row['proveedor_nombre']:
                doc["proveedor_nombre"] = row['proveedor_nombre']
                doc["proveedor_cuit"] = row['proveedor_cuit']
            if row['tipo_operacion'] == 'Pago' and row['pago_asiento_id'] is not None:
                doc["pago_monto"] = float(row['pago_monto']) if row['pago_monto'] is not None else None
                doc["pago_asiento_id"] = row['pago_asiento_id']
                doc["pago_observaciones"] = row['pago_observaciones']
                doc["pago_metodo_pago"] = (
                    'Efectivo' if row['pago_metodo_rol'] == 'CAJA'
                    else 'Transferencia' if row['pago_metodo_rol'] == 'BANCO'
                    else None
                )
            if row['gasto_descripcion']:
                doc["gasto_descripcion"] = row['gasto_descripcion']
                doc["gasto_cuenta_nombre"] = row['gasto_cuenta_nombre']
                doc["gasto_cuenta_codigo"] = row['gasto_cuenta_codigo']
            if row['comprobante_padre_id'] and row['padre_tipo_comprobante']:
                doc["padre_info"] = {
                    "tipo_comprobante": row['padre_tipo_comprobante'],
                    "nro_comprobante": row['padre_nro_comprobante'],
                    "fecha_emision": str(row['padre_fecha_emision']) if row['padre_fecha_emision'] else None,
                    "total": float(row['padre_total']) if row['padre_total'] else 0,
                    "entidad": row['padre_entidad'],
                    "tipo_operacion": row['padre_tipo_operacion'],
                }
                doc["nota_motivo"] = row['motivo_nota'] or ''
            documentos_agrupados[doc_id] = doc

        items = documentos_agrupados[doc_id]["items_originales"]
        existing_ids = {i['producto_id'] for i in items}

        if row['vd_producto_id'] is not None and row['vd_producto_id'] not in existing_ids:
            items.append({
                "producto_id": row['vd_producto_id'],
                "nombre": row['vd_producto_nombre'],
                "cantidad": row['vd_cantidad'],
                "precio_unitario": float(row['vd_precio_unitario'])
            })
        elif row['cd_producto_id'] is not None and row['cd_producto_id'] not in existing_ids:
            items.append({
                "producto_id": row['cd_producto_id'],
                "nombre": row['cd_producto_nombre'],
                "cantidad": row['cd_cantidad'],
                "precio_unitario": float(row['cd_costo_unitario'])
            })

    return list(documentos_agrupados.values())


CODIGOS_AFIP_NOTA = {
    ('Nota de Crédito', 'A'): '03',
    ('Nota de Crédito', 'B'): '08',
    ('Nota de Débito', 'A'): '02',
    ('Nota de Débito', 'B'): '07',
}


async def obtener_nota_para_imprimir(conn: Connection, doc_id: int) -> dict:
    row = await conn.fetchrow("""
        SELECT
            dc.id, dc.tipo_comprobante, dc.nro_comprobante, dc.fecha_emision, dc.total,
            dc.comprobante_padre_id,
            padre.tipo_comprobante AS padre_tipo_comprobante,
            padre.nro_comprobante AS padre_nro_comprobante,
            padre.fecha_emision AS padre_fecha_emision,
            padre.total AS padre_total,
            padre.cliente_proveedor_nombre AS cliente_nombre,
            padre.cliente_proveedor_identificacion AS cliente_identificacion,
            padre.condicion_iva AS cliente_condicion_iva,
            padre.venta_id AS padre_venta_id,
            dc.motivo_nota
        FROM documentos_contables dc
        LEFT JOIN documentos_contables padre ON dc.comprobante_padre_id = padre.id
        WHERE dc.id = $1;
    """, doc_id)

    if not row:
        raise NotFoundException(detail=f"El documento con ID {doc_id} no existe.")

    if row['comprobante_padre_id'] is None:
        raise BadRequestException(detail="Este documento no es una nota de crédito/débito.")

    if row['padre_venta_id'] is None:
        raise BadRequestException(detail="Solo se pueden imprimir notas emitidas sobre una venta.")

    tipo_comprobante = row['tipo_comprobante'] or ''
    partes = tipo_comprobante.split(' ')
    letra = partes[-1] if partes else 'B'
    if letra not in ('A', 'B'):
        letra = 'B'
    es_credito = 'crédito' in tipo_comprobante.lower() or 'credito' in tipo_comprobante.lower()
    tipo_nota_titulo = 'NOTA DE CRÉDITO' if es_credito else 'NOTA DE DÉBITO'
    codigo_afip = CODIGOS_AFIP_NOTA.get((('Nota de Crédito' if es_credito else 'Nota de Débito'), letra), '00')

    motivo = row['motivo_nota'] or ''

    total = float(row['total'])
    nota = {
        'id': row['id'],
        'tipo_comprobante': tipo_comprobante,
        'tipo_nota_titulo': tipo_nota_titulo,
        'letra': letra,
        'codigo_afip': codigo_afip,
        'nro_comprobante': row['nro_comprobante'],
        'fecha_emision': str(row['fecha_emision']),
        'total': total,
        'motivo': motivo,
        'padre_tipo_comprobante': row['padre_tipo_comprobante'],
        'padre_nro_comprobante': row['padre_nro_comprobante'],
        'padre_fecha_emision': str(row['padre_fecha_emision']) if row['padre_fecha_emision'] else None,
        'padre_total': float(row['padre_total']) if row['padre_total'] is not None else 0.0,
        'cliente_nombre': row['cliente_nombre'],
        'cliente_identificacion': row['cliente_identificacion'],
        'cliente_condicion_iva': row['cliente_condicion_iva'],
    }

    if letra == 'A':
        neto = round(total / 1.21, 2)
        nota['subtotal_neto'] = neto
        nota['iva_21'] = round(total - neto, 2)

    return nota


async def procesar_nota_venta(conn: Connection, nota_data: NotaVentaCreate) -> dict:
    async with conn.transaction():
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

        doc_id = await conn.fetchval("""
            INSERT INTO documentos_contables (
                tipo_operacion, tipo_comprobante, nro_comprobante, fecha_emision, total, comprobante_padre_id, motivo_nota
            ) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id;
        """, 'Ajuste/Nota', nota_data.tipo_comprobante, nro_comprobante, nota_data.fecha, nota_data.total_modificado, nota_data.comprobante_padre_id, nota_data.motivo)

        costo_total_modificado = 0.0
        es_ajuste_fisico = False

        for item in nota_data.items_afectados:
            if item.cantidad > 0:
                es_ajuste_fisico = True
                if is_credito:
                    await conn.execute("UPDATE producto SET stock = stock + $1 WHERE id = $2", item.cantidad, item.producto_id)
                else:
                    await conn.execute("UPDATE producto SET stock = stock - $1 WHERE id = $2", item.cantidad, item.producto_id)

                costo = await conn.fetchval("SELECT costo FROM producto WHERE id = $1", item.producto_id)
                costo_total_modificado += float(costo) * item.cantidad

            elif item.cantidad == 0 and item.nuevo_precio is not None:
                await conn.execute("UPDATE producto SET precio = $1 WHERE id = $2", item.nuevo_precio, item.producto_id)

        cs = await resolver_cuentas_sistema(conn, ['CAJA', 'BANCO', 'VENTAS', 'MERCADERIAS', 'CMV'])

        cuenta_cobro_id = None
        if padre['asiento_id']:
            cuenta_cobro_id = await conn.fetchval("""
                SELECT ad.cuenta_id FROM asientos_detalle ad
                WHERE ad.asiento_id = $1 AND ad.cuenta_id IN ($2, $3) LIMIT 1
            """, padre['asiento_id'], cs['CAJA'], cs['BANCO'])

        if not cuenta_cobro_id:
            cuenta_cobro_id = cs['CAJA']

        c_ventas = cs['VENTAS']
        c_merca = cs['MERCADERIAS']
        c_cmv = cs['CMV']

        fecha_asiento = datetime.combine(nota_data.fecha, datetime.now().time())
        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            fecha_asiento, f"{nota_data.tipo_comprobante} - Ref. Doc #{nota_data.comprobante_padre_id}: {nota_data.motivo}"
        )

        renglones = []
        if is_credito:
            renglones.extend([
                (asiento_id, c_ventas, nota_data.total_modificado, 0.00),
                (asiento_id, cuenta_cobro_id, 0.00, nota_data.total_modificado)
            ])
            if es_ajuste_fisico and costo_total_modificado > 0:
                renglones.extend([
                    (asiento_id, c_merca, costo_total_modificado, 0.00),
                    (asiento_id, c_cmv, 0.00, costo_total_modificado)
                ])
        else:
            renglones.extend([
                (asiento_id, cuenta_cobro_id, nota_data.total_modificado, 0.00),
                (asiento_id, c_ventas, 0.00, nota_data.total_modificado)
            ])
            if es_ajuste_fisico and costo_total_modificado > 0:
                renglones.extend([
                    (asiento_id, c_cmv, costo_total_modificado, 0.00),
                    (asiento_id, c_merca, 0.00, costo_total_modificado)
                ])

        await conn.executemany(
            "INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) VALUES ($1, $2, $3, $4)",
            renglones
        )

        return {"id": doc_id, "asiento_id": asiento_id, "nro_comprobante": nro_comprobante, "mensaje": "Nota sobre Venta registrada exitosamente."}


async def procesar_nota_compra(conn: Connection, nota_data: NotaCompraCreate) -> dict:
    async with conn.transaction():
        padre = await conn.fetchrow("""
            SELECT dc.id, cm.asiento_id
            FROM documentos_contables dc
            LEFT JOIN compras_mercaderia cm ON dc.compra_id = cm.id
            WHERE dc.id = $1
        """, nota_data.comprobante_padre_id)

        if not padre:
            raise NotFoundException("Comprobante original no encontrado.")

        is_credito = "crédito" in nota_data.tipo_comprobante.lower() or "credito" in nota_data.tipo_comprobante.lower()

        doc_id = await conn.fetchval("""
            INSERT INTO documentos_contables (
                tipo_operacion, tipo_comprobante, nro_comprobante, fecha_emision, total, comprobante_padre_id, motivo_nota
            ) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id;
        """, 'Ajuste/Nota', nota_data.tipo_comprobante, nota_data.nro_comprobante_recibido, nota_data.fecha, nota_data.total_modificado, nota_data.comprobante_padre_id, nota_data.motivo)

        for item in nota_data.items_afectados:
            if item.cantidad > 0:
                if is_credito:
                    await conn.execute("UPDATE producto SET stock = stock - $1 WHERE id = $2", item.cantidad, item.producto_id)
                else:
                    await conn.execute("UPDATE producto SET stock = stock + $1 WHERE id = $2", item.cantidad, item.producto_id)
            elif item.cantidad == 0 and item.nuevo_costo is not None:
                await conn.execute("UPDATE producto SET costo = $1 WHERE id = $2", item.nuevo_costo, item.producto_id)

        cs = await resolver_cuentas_sistema(conn, ['CAJA', 'BANCO', 'MERCADERIAS', 'PROVEEDORES'])

        cuenta_pago_id = None
        if padre['asiento_id']:
            cuenta_pago_id = await conn.fetchval("""
                SELECT ad.cuenta_id FROM asientos_detalle ad
                WHERE ad.asiento_id = $1 AND ad.cuenta_id IN ($2, $3, $4) LIMIT 1
            """, padre['asiento_id'], cs['CAJA'], cs['BANCO'], cs['PROVEEDORES'])

        if not cuenta_pago_id:
            cuenta_pago_id = cs['CAJA']

        c_merca = cs['MERCADERIAS']

        fecha_asiento = datetime.combine(nota_data.fecha, datetime.now().time())
        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            fecha_asiento, f"{nota_data.tipo_comprobante} - Ref. Doc #{nota_data.comprobante_padre_id}: {nota_data.motivo}"
        )

        renglones = []
        if is_credito:
            renglones.extend([
                (asiento_id, cuenta_pago_id, nota_data.total_modificado, 0.00),
                (asiento_id, c_merca, 0.00, nota_data.total_modificado)
            ])
        else:
            renglones.extend([
                (asiento_id, c_merca, nota_data.total_modificado, 0.00),
                (asiento_id, cuenta_pago_id, 0.00, nota_data.total_modificado)
            ])

        await conn.executemany(
            "INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) VALUES ($1, $2, $3, $4)",
            renglones
        )

        return {"id": doc_id, "asiento_id": asiento_id, "nro_comprobante": nota_data.nro_comprobante_recibido, "mensaje": "Nota sobre Compra registrada exitosamente."}
