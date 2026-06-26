# src/services/proveedorServices.py
from asyncpg import Connection
from schemas.proveedorSchema import PagoProveedorCreate
from utils.exceptions import NotFoundException, DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema
from services.cierreServices import validar_periodo_abierto
from services.proveedorMaestroServices import obtener_deudas


async def obtener_deudas_activas(conn: Connection) -> list[dict]:
    return await obtener_deudas(conn)


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

        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            pago_data.fecha, descripcion
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
