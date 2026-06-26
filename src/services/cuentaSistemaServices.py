from asyncpg import Connection
from utils.exceptions import DatabaseException, NotFoundException, BadRequestException

ROLES_VALIDOS = {'CAJA', 'BANCO', 'MERCADERIAS', 'VENTAS', 'CMV', 'CAPITAL', 'PROVEEDORES', 'RESULTADO_EJERCICIO'}


async def resolver_cuentas_sistema(conn: Connection, roles: list[str]) -> dict[str, int]:
    rows = await conn.fetch(
        "SELECT rol, cuenta_id FROM cuentas_sistema WHERE rol = ANY($1::text[]);",
        roles
    )
    resultado = {row['rol']: row['cuenta_id'] for row in rows}
    faltantes = set(roles) - set(resultado.keys())
    if faltantes:
        raise DatabaseException(
            detail=f"Configuración contable incompleta. Roles sin asignar: {', '.join(sorted(faltantes))}. "
                   f"Configure las cuentas del sistema antes de operar."
        )
    return resultado


async def obtener_configuracion(conn: Connection) -> dict:
    rows = await conn.fetch("""
        SELECT cs.rol, cs.cuenta_id, c.nombre AS cuenta_nombre, c.codigo AS cuenta_codigo
        FROM cuentas_sistema cs
        JOIN cuentas c ON cs.cuenta_id = c.id
        ORDER BY cs.rol;
    """)
    return {
        "data": [dict(row) for row in rows],
        "roles_disponibles": sorted(ROLES_VALIDOS)
    }


async def actualizar_rol(conn: Connection, rol: str, cuenta_id: int) -> dict:
    if rol not in ROLES_VALIDOS:
        raise BadRequestException(detail=f"Rol '{rol}' no es válido. Roles permitidos: {', '.join(sorted(ROLES_VALIDOS))}")

    cuenta = await conn.fetchrow("SELECT id, nombre, codigo FROM cuentas WHERE id = $1;", cuenta_id)
    if not cuenta:
        raise NotFoundException(detail=f"La cuenta con ID {cuenta_id} no existe.")

    await conn.execute("""
        INSERT INTO cuentas_sistema (rol, cuenta_id) VALUES ($1, $2)
        ON CONFLICT (rol) DO UPDATE SET cuenta_id = $2;
    """, rol, cuenta_id)

    return {
        "rol": rol,
        "cuenta_id": cuenta_id,
        "cuenta_nombre": cuenta['nombre'],
        "cuenta_codigo": cuenta['codigo']
    }
