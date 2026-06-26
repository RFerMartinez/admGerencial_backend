from asyncpg import Connection
from schemas.proveedorMaestroSchema import ProveedorCreate
from utils.exceptions import NotFoundException, BadRequestException, DatabaseException


async def obtener_todos(conn: Connection) -> list[dict]:
    rows = await conn.fetch("""
        SELECT id, nombre, cuit, domicilio, telefono
        FROM proveedores
        ORDER BY nombre;
    """)
    return [dict(row) for row in rows]


async def obtener_por_id(conn: Connection, proveedor_id: int) -> dict:
    row = await conn.fetchrow(
        "SELECT id, nombre, cuit, domicilio, telefono FROM proveedores WHERE id = $1;",
        proveedor_id
    )
    if not row:
        raise NotFoundException(detail=f"El proveedor con ID {proveedor_id} no existe.")
    return dict(row)


async def crear(conn: Connection, data: ProveedorCreate) -> dict:
    row = await conn.fetchrow("""
        INSERT INTO proveedores (nombre, cuit, domicilio, telefono)
        VALUES ($1, $2, $3, $4) RETURNING id, nombre, cuit, domicilio, telefono;
    """, data.nombre, data.cuit, data.domicilio, data.telefono)
    return dict(row)


async def actualizar(conn: Connection, proveedor_id: int, data: ProveedorCreate) -> dict:
    row = await conn.fetchrow("""
        UPDATE proveedores SET nombre = $1, cuit = $2, domicilio = $3, telefono = $4
        WHERE id = $5 RETURNING id, nombre, cuit, domicilio, telefono;
    """, data.nombre, data.cuit, data.domicilio, data.telefono, proveedor_id)
    if not row:
        raise NotFoundException(detail=f"El proveedor con ID {proveedor_id} no existe.")
    return dict(row)


async def eliminar(conn: Connection, proveedor_id: int) -> None:
    existe = await conn.fetchval("SELECT id FROM proveedores WHERE id = $1;", proveedor_id)
    if not existe:
        raise NotFoundException(detail=f"El proveedor con ID {proveedor_id} no existe.")
    try:
        await conn.execute("DELETE FROM proveedores WHERE id = $1;", proveedor_id)
    except Exception:
        raise BadRequestException(
            detail="No se puede eliminar el proveedor porque tiene compras, gastos o pagos asociados."
        )


async def obtener_deudas(conn: Connection) -> list[dict]:
    query = """
        SELECT
            p.id, p.nombre, p.cuit,
            COALESCE(deuda.total_deuda, 0) - COALESCE(pagos.total_pagado, 0) AS saldo_pendiente
        FROM proveedores p
        LEFT JOIN (
            SELECT proveedor_id, SUM(total_deuda) AS total_deuda FROM (
                SELECT proveedor_id, SUM(total) AS total_deuda
                FROM compras_mercaderia
                WHERE proveedor_id IS NOT NULL
                GROUP BY proveedor_id
                UNION ALL
                SELECT proveedor_id, SUM(monto) AS total_deuda
                FROM gastos
                WHERE proveedor_id IS NOT NULL
                GROUP BY proveedor_id
            ) sub
            GROUP BY proveedor_id
        ) deuda ON p.id = deuda.proveedor_id
        LEFT JOIN (
            SELECT proveedor_id, SUM(monto) AS total_pagado
            FROM pagos_proveedor
            GROUP BY proveedor_id
        ) pagos ON p.id = pagos.proveedor_id
        WHERE COALESCE(deuda.total_deuda, 0) - COALESCE(pagos.total_pagado, 0) > 0
        ORDER BY saldo_pendiente DESC;
    """
    rows = await conn.fetch(query)
    return [dict(row) for row in rows]
