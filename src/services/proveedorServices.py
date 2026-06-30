# src/services/proveedorServices.py
from asyncpg import Connection
from schemas.proveedorSchema import PagoProveedorCreate
from utils.exceptions import NotFoundException, DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema
from services.cierreServices import validar_periodo_abierto
from services.proveedorMaestroServices import obtener_deudas


async def obtener_deudas_activas(conn: Connection) -> list[dict]:
    return await obtener_deudas(conn)


async def obtener_movimientos(conn: Connection, proveedor_id: int) -> list[dict]:
    prov = await conn.fetchrow("SELECT id FROM proveedores WHERE id = $1;", proveedor_id)
    if not prov:
        raise NotFoundException(detail=f"El proveedor con ID {proveedor_id} no existe.")

    # Nota: compras_mercaderia y gastos no guardan tipo/nro de comprobante en sus propias
    # columnas; ese detalle vive en documentos_contables (vinculado por compra_id/gasto_id),
    # por eso se hace LEFT JOIN en vez de leerlo directo de la tabla operativa.
    query = """
        SELECT 'Compra' AS tipo, cm.fecha,
               COALESCE('Compra s/ ' || dc.tipo_comprobante || ' ' || dc.nro_comprobante, 'Compra de mercadería') AS descripcion,
               cm.total AS monto
        FROM compras_mercaderia cm
        LEFT JOIN documentos_contables dc ON dc.compra_id = cm.id
        WHERE cm.proveedor_id = $1 AND cm.metodo_pago = 'Cuenta Corriente'

        UNION ALL

        SELECT 'Gasto' AS tipo, g.fecha,
               COALESCE('Gasto s/ ' || dc.tipo_comprobante || ' ' || dc.nro_comprobante || ' - ' || g.descripcion, 'Gasto: ' || g.descripcion) AS descripcion,
               g.monto
        FROM gastos g
        LEFT JOIN documentos_contables dc ON dc.gasto_id = g.id
        WHERE g.proveedor_id = $1 AND g.metodo_pago = 'Cuenta Corriente'

        UNION ALL

        SELECT 'Pago' AS tipo, p.fecha,
               'Pago registrado' AS descripcion,
               -p.monto AS monto
        FROM pagos_proveedor p
        WHERE p.proveedor_id = $1

        ORDER BY fecha ASC;
    """
    rows = await conn.fetch(query, proveedor_id)

    movimientos = []
    saldo = 0.0
    for row in rows:
        saldo += float(row['monto'])
        movimientos.append({
            'tipo': row['tipo'],
            'fecha': row['fecha'],
            'descripcion': row['descripcion'],
            'monto': float(row['monto']),
            'saldo_acumulado': round(saldo, 2),
        })

    movimientos.reverse()
    return movimientos


async def registrar_pago(conn: Connection, pago_data: PagoProveedorCreate) -> dict:
    async with conn.transaction():
        await validar_periodo_abierto(conn, pago_data.fecha)

        # 1. Verificar que el proveedor exista
        prov = await conn.fetchrow(
            "SELECT id, nombre FROM proveedores WHERE id = $1;",
            pago_data.proveedor_id
        )
        if not prov:
            raise NotFoundException(detail=f"El proveedor con ID {pago_data.proveedor_id} no existe.")

        # 2. Resolver cuentas del sistema
        rol_salida = 'CAJA' if pago_data.metodo_pago == 'Efectivo' else 'BANCO'
        config = await resolver_cuentas_sistema(conn, [rol_salida, 'PROVEEDORES'])
        cuenta_salida_id = config[rol_salida]
        cuenta_proveedores_id = config['PROVEEDORES']

        # 3. Asiento contable: DEBE Proveedores, HABER Caja/Banco
        descripcion = pago_data.observaciones.strip() if pago_data.observaciones else f"Pago a {prov['nombre']} s/ {pago_data.tipo_comprobante} {pago_data.nro_comprobante_recibido}"

        fecha_naive = pago_data.fecha.replace(tzinfo=None) if pago_data.fecha.tzinfo else pago_data.fecha
        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            fecha_naive, descripcion
        )

        renglones_contables = [
            (asiento_id, cuenta_proveedores_id, pago_data.monto_pagado, 0.00),
            (asiento_id, cuenta_salida_id, 0.00, pago_data.monto_pagado)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber)
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        # 4. Registro en pagos_proveedor (tracking individual)
        await conn.execute("""
            INSERT INTO pagos_proveedor (proveedor_id, fecha, monto, asiento_id)
            VALUES ($1, $2, $3, $4);
        """, pago_data.proveedor_id, pago_data.fecha, pago_data.monto_pagado, asiento_id)

        # 5. Registro documental
        await conn.execute("""
            INSERT INTO documentos_contables (
                tipo_operacion, fecha_emision, tipo_comprobante, nro_comprobante,
                entidad_nombre, total, comprobante_padre_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7);
        """,
            'Pago',
            pago_data.fecha,
            pago_data.tipo_comprobante,
            pago_data.nro_comprobante_recibido,
            prov['nombre'],
            pago_data.monto_pagado,
            pago_data.comprobante_padre_id
        )

        return {"asiento_id": asiento_id}
