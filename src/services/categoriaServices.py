import asyncpg
from asyncpg import Connection
from schemas.categoriaSchema import CategoriaCreate, CategoriaUpdate
from utils.exceptions import NotFoundException, BadRequestException, DatabaseException

async def get_all_categorias(conn: Connection) -> list[dict]:
    try:
        query = "SELECT nombre FROM categorias ORDER BY nombre ASC;"
        records = await conn.fetch(query)
        return [dict(record) for record in records]
    except Exception as e:
        raise DatabaseException(f"Error al listar categorías: {str(e)}")

async def get_categoria_by_nombre(conn: Connection, nombre: str) -> dict:
    query = "SELECT nombre FROM categorias WHERE nombre = $1;"
    record = await conn.fetchrow(query, nombre)
    
    if not record:
        raise NotFoundException(detail=f"La categoría '{nombre}' no fue encontrada.")
    
    return dict(record)

async def create_categoria(conn: Connection, categoria: CategoriaCreate) -> dict:
    query = """
        INSERT INTO categorias (nombre) 
        VALUES ($1) 
        RETURNING nombre;
    """
    try:
        record = await conn.fetchrow(query, categoria.nombre)
        return dict(record)
    except asyncpg.exceptions.UniqueViolationError:
        raise BadRequestException(detail=f"La categoría '{categoria.nombre}' ya existe.")
    except Exception as e:
        raise DatabaseException(f"Error al crear la categoría: {str(e)}")

async def update_categoria(conn: Connection, nombre_actual: str, data_update: CategoriaUpdate) -> dict:
    # 1. Verificamos que la categoría actual exista
    await get_categoria_by_nombre(conn, nombre_actual)
    
    query = """
        UPDATE categorias 
        SET nombre = $1 
        WHERE nombre = $2 
        RETURNING nombre;
    """
    try:
        record = await conn.fetchrow(query, data_update.nombre, nombre_actual)
        return dict(record)
    except asyncpg.exceptions.UniqueViolationError:
        raise BadRequestException(detail=f"El nombre '{data_update.nombre}' ya está siendo usado por otra categoría.")
    except Exception as e:
        raise DatabaseException(f"Error al actualizar la categoría: {str(e)}")

async def delete_categoria(conn: Connection, nombre: str) -> None:
    # Verificamos si existe antes de borrar
    await get_categoria_by_nombre(conn, nombre)
    
    try:
        query = "DELETE FROM categorias WHERE nombre = $1;"
        await conn.execute(query, nombre)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail=f"No se puede eliminar la categoría '{nombre}' porque tiene productos asociados. Reasigna los productos primero.")
    except Exception as e:
        raise DatabaseException(f"Error al eliminar la categoría: {str(e)}")

