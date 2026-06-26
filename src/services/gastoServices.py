from asyncpg import Connection
from datetime import datetime
from schemas.gastoSchema import GastoCreate
from utils.exceptions import NotFoundException, DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema
from services.cierreServices import validar_periodo_abierto


async def registrar_gasto(conn: Connection, gasto_data: GastoCreate) -> dict:
    async with conn.transaction():

        await validar_periodo_abierto(conn, gasto_data.fecha)

        # 1. Validar cuenta al debe
        cuenta_debe = await conn.fetchrow(
            "SELECT id, nombre FROM cuentas WHERE id = $1;", gasto_data.cuenta_debe_id
        )
        if not cuenta_debe:
            raise NotFoundException(detail=f"La cuenta con ID {gasto_data.cuenta_debe_id} no existe.")

        # 2. Resolver cuenta al haber
        if gasto_data.proveedor_id is not None:
            prov = await conn.fetchrow(
                "SELECT id, nombre FROM proveedores WHERE id = $1;",
                gasto_data.proveedor_id
            )
            if not prov:
                raise NotFoundException(detail=f"El proveedor con ID {gasto_data.proveedor_id} no existe.")

            config = await resolver_cuentas_sistema(conn, ['PROVEEDORES'])
            cuenta_haber_id = config['PROVEEDORES']
            entidad_nombre = prov['nombre']
        else:
            rol = 'CAJA' if gasto_data.metodo_pago == 'Efectivo' else 'BANCO'
            config = await resolver_cuentas_sistema(conn, [rol])
            cuenta_haber_id = config[rol]
            entidad_nombre = None

        # 3. Asiento contable
        descripcion = f"Gasto s/ {gasto_data.tipo_comprobante} {gasto_data.nro_comprobante} - {gasto_data.descripcion}"
        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            datetime.now(), descripcion
        )

        # 4. Registro operativo
        gasto_id = await conn.fetchval("""
            INSERT INTO gastos (fecha, descripcion, cuenta_debe_id, monto, asiento_id, proveedor_id)
            VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;
        """, gasto_data.fecha, gasto_data.descripcion, gasto_data.cuenta_debe_id,
            gasto_data.monto, asiento_id, gasto_data.proveedor_id)

        # 5. Registro documental
        await conn.execute("""
            INSERT INTO documentos_contables (
                tipo_operacion, tipo_comprobante, nro_comprobante, fecha_emision, total,
                entidad_nombre, gasto_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7);
        """,
            'Gasto',
            gasto_data.tipo_comprobante,
            gasto_data.nro_comprobante,
            gasto_data.fecha,
            gasto_data.monto,
            entidad_nombre,
            gasto_id
        )

        # 6. Partida doble
        renglones = [
            (asiento_id, gasto_data.cuenta_debe_id, gasto_data.monto, 0.00),
            (asiento_id, cuenta_haber_id, 0.00, gasto_data.monto)
        ]
        await conn.executemany(
            "INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) VALUES ($1, $2, $3, $4);",
            renglones
        )

        return {
            "id": gasto_id,
            "fecha": gasto_data.fecha,
            "monto": gasto_data.monto,
            "asiento_id": asiento_id,
            "tipo_comprobante": gasto_data.tipo_comprobante,
            "nro_comprobante": gasto_data.nro_comprobante
        }


async def obtener_gastos(conn: Connection) -> list[dict]:
    rows = await conn.fetch("""
        SELECT g.id, g.fecha, g.descripcion,
               c.nombre AS cuenta_nombre, c.codigo AS cuenta_codigo,
               g.monto
        FROM gastos g
        JOIN cuentas c ON g.cuenta_debe_id = c.id
        ORDER BY g.fecha DESC, g.id DESC;
    """)
    return [dict(row) for row in rows]
