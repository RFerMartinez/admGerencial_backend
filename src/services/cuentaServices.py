# src/services/cuentaServices.py
import asyncpg
from asyncpg import Connection
from schemas.cuentaSchema import CuentaCreate, CuentaUpdate
from utils.exceptions import NotFoundException, BadRequestException, DatabaseException

async def get_all_cuentas(conn: Connection) -> list[dict]:
    try:
        # Ordenamos por código para preservar la estructura jerárquica del plan de cuentas
        query = "SELECT id, codigo, nombre, tipo FROM cuentas ORDER BY codigo ASC, id ASC;"
        records = await conn.fetch(query)
        return [dict(record) for record in records]
    except Exception as e:
        raise DatabaseException(f"Error al listar las cuentas contables: {str(e)}")

async def get_cuenta_by_id(conn: Connection, cuenta_id: int) -> dict:
    query = "SELECT id, codigo, nombre, tipo FROM cuentas WHERE id = $1;"
    record = await conn.fetchrow(query, cuenta_id)
    
    if not record:
        raise NotFoundException(detail=f"La cuenta contable con ID {cuenta_id} no fue encontrada.")
    
    return dict(record)

async def create_cuenta(conn: Connection, cuenta: CuentaCreate) -> dict:
    query = """
        INSERT INTO cuentas (codigo, nombre, tipo) 
        VALUES ($1, $2, $3) 
        RETURNING id, codigo, nombre, tipo;
    """
    try:
        record = await conn.fetchrow(query, cuenta.codigo, cuenta.nombre, cuenta.tipo)
        return dict(record)
    except asyncpg.exceptions.CheckViolationError:
        raise BadRequestException(detail="El tipo de cuenta proporcionado no cumple con las categorías permitidas.")
    except Exception as e:
        raise DatabaseException(f"Error al registrar la cuenta contable: {str(e)}")

async def update_cuenta(conn: Connection, cuenta_id: int, data_update: CuentaUpdate) -> dict:
    # 1. Verificar existencia
    cuenta_actual = await get_cuenta_by_id(conn, cuenta_id)
    
    # 2. Asignar valores dinámicos
    codigo = data_update.codigo if data_update.codigo is not None else cuenta_actual["codigo"]
    nombre = data_update.nombre if data_update.nombre is not None else cuenta_actual["nombre"]
    tipo = data_update.tipo if data_update.tipo is not None else cuenta_actual["tipo"]

    query = """
        UPDATE cuentas 
        SET codigo = $1, nombre = $2, tipo = $3 
        WHERE id = $4 
        RETURNING id, codigo, nombre, tipo;
    """
    try:
        record = await conn.fetchrow(query, codigo, nombre, tipo, cuenta_id)
        return dict(record)
    except asyncpg.exceptions.CheckViolationError:
        raise BadRequestException(detail="El tipo de cuenta modificado no es válido.")
    except Exception as e:
        raise DatabaseException(f"Error al actualizar la cuenta contable: {str(e)}")

async def delete_cuenta(conn: Connection, cuenta_id: int) -> None:
    # Verificar si existe
    await get_cuenta_by_id(conn, cuenta_id)
    
    try:
        query = "DELETE FROM cuentas WHERE id = $1;"
        await conn.execute(query, cuenta_id)
    except asyncpg.exceptions.ForeignKeyViolationError:
        # Se activa si la cuenta ya tiene renglones en asientos_detalle
        raise BadRequestException(
            detail="No es posible eliminar la cuenta contable porque registra movimientos en el Libro Diario."
        )
    except Exception as e:
        raise DatabaseException(f"Error al eliminar la cuenta contable: {str(e)}")

