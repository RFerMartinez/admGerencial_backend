# src/services/productoServices.py
import asyncpg
from asyncpg import Connection
from schemas.productoSchema import ProductoCreate, ProductoUpdate
from utils.exceptions import NotFoundException, BadRequestException, DatabaseException

async def get_all_productos(conn: Connection) -> list[dict]:
    try:
        # Añadimos 'costo' a la lectura masiva
        query = "SELECT id, nombre, precio, costo, stock, tipo FROM producto ORDER BY id ASC;"
        records = await conn.fetch(query)
        return [dict(record) for record in records]
    except Exception as e:
        raise DatabaseException(f"Error al listar productos: {str(e)}")

async def get_producto_by_id(conn: Connection, producto_id: int) -> dict:
    # Añadimos 'costo' a la lectura individual
    query = "SELECT id, nombre, precio, costo, stock, tipo FROM producto WHERE id = $1;"
    record = await conn.fetchrow(query, producto_id)
    
    if not record:
        raise NotFoundException(detail=f"El producto con ID {producto_id} no fue encontrado.")
    
    return dict(record)

async def create_producto(conn: Connection, producto: ProductoCreate) -> dict:
    # Modificamos el INSERT para incluir la columna costo
    query = """
        INSERT INTO producto (nombre, tipo, precio, costo, stock) 
        VALUES ($1, $2, $3, $4, $5) 
        RETURNING id, nombre, precio, costo, stock, tipo;
    """
    try:
        record = await conn.fetchrow(
            query, 
            producto.nombre, 
            producto.tipo, 
            producto.precio, 
            producto.costo,  # <-- Pasamos el costo asignado
            producto.stock
        )
        return dict(record)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail=f"La categoría '{producto.tipo}' no existe en el sistema.")
    except Exception as e:
        raise DatabaseException(f"Error al crear el producto: {str(e)}")

async def update_producto(conn: Connection, producto_id: int, data_update: ProductoUpdate) -> dict:
    # 1. Verificar si existe (Trae los datos actuales incluyendo el costo)
    producto_actual = await get_producto_by_id(conn, producto_id)
    
    # 2. Reemplazar campos dinámicamente si vienen en el JSON
    nombre = data_update.nombre if data_update.nombre is not None else producto_actual["nombre"]
    tipo = data_update.tipo if data_update.tipo is not None else producto_actual["tipo"]
    precio = data_update.precio if data_update.precio is not None else producto_actual["precio"]
    costo = data_update.costo if data_update.costo is not None else producto_actual["costo"]  # <-- NUEVO MAPEO
    stock = data_update.stock if data_update.stock is not None else producto_actual["stock"]

    # Modificamos el UPDATE para persistir el costo editado
    query = """
        UPDATE producto 
        SET nombre = $1, tipo = $2, precio = $3, costo = $4, stock = $5 
        WHERE id = $6 
        RETURNING id, nombre, precio, costo, stock, tipo;
    """
    try:
        record = await conn.fetchrow(query, nombre, tipo, precio, costo, stock, producto_id)
        return dict(record)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail=f"La categoría '{tipo}' no existe en el sistema.")
    except Exception as e:
        raise DatabaseException(f"Error al actualizar el producto: {str(e)}")

async def delete_producto(conn: Connection, producto_id: int) -> None:
    await get_producto_by_id(conn, producto_id)
    
    try:
        query = "DELETE FROM producto WHERE id = $1;"
        await conn.execute(query, producto_id)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail="No se puede eliminar el producto porque tiene movimientos asociados.")
    except Exception as e:
        raise DatabaseException(f"Error al eliminar el producto: {str(e)}")

