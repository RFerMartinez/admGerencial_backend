# src/services/productoServices.py
import asyncpg
from asyncpg import Connection
from schemas.productoSchema import ProductoCreate, ProductoUpdate
from utils.exceptions import NotFoundException, BadRequestException, DatabaseException

async def get_all_productos(conn: Connection) -> list[dict]:
    try:
        query = "SELECT id, nombre, precio, stock, tipo FROM producto ORDER BY id ASC;"
        records = await conn.fetch(query)
        return [dict(record) for record in records]
    except Exception as e:
        raise DatabaseException(f"Error al listar productos: {str(e)}")

async def get_producto_by_id(conn: Connection, producto_id: int) -> dict:
    query = "SELECT id, nombre, precio, stock, tipo FROM producto WHERE id = $1;"
    record = await conn.fetchrow(query, producto_id)
    
    if not record:
        raise NotFoundException(detail=f"El producto con ID {producto_id} no fue encontrado.")
    
    return dict(record)

async def create_producto(conn: Connection, producto: ProductoCreate) -> dict:
    query = """
        INSERT INTO producto (nombre, tipo, precio, stock) 
        VALUES ($1, $2, $3, $4) 
        RETURNING id, nombre, precio, stock, tipo;
    """
    try:
        record = await conn.fetchrow(
            query, 
            producto.nombre, 
            producto.tipo, 
            producto.precio, 
            producto.stock
        )
        return dict(record)
    except asyncpg.exceptions.ForeignKeyViolationError:
        # Capturamos el error si la categoría enviada en "tipo" no existe en la BD
        raise BadRequestException(detail=f"La categoría '{producto.tipo}' no existe en el sistema.")
    except Exception as e:
        raise DatabaseException(f"Error al crear el producto: {str(e)}")

async def update_producto(conn: Connection, producto_id: int, data_update: ProductoUpdate) -> dict:
    # 1. Verificar si existe
    producto_actual = await get_producto_by_id(conn, producto_id)
    
    # 2. Construir campos dinámicamente
    nombre = data_update.nombre if data_update.nombre is not None else producto_actual["nombre"]
    tipo = data_update.tipo if data_update.tipo is not None else producto_actual["tipo"]
    precio = data_update.precio if data_update.precio is not None else producto_actual["precio"]
    stock = data_update.stock if data_update.stock is not None else producto_actual["stock"]

    query = """
        UPDATE producto 
        SET nombre = $1, tipo = $2, precio = $3, stock = $4 
        WHERE id = $5 
        RETURNING id, nombre, precio, stock, tipo;
    """
    try:
        record = await conn.fetchrow(query, nombre, tipo, precio, stock, producto_id)
        return dict(record)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail=f"La categoría '{tipo}' no existe en el sistema.")
    except Exception as e:
        raise DatabaseException(f"Error al actualizar el producto: {str(e)}")

async def delete_producto(conn: Connection, producto_id: int) -> None:
    # Verificamos si existe antes de borrar
    await get_producto_by_id(conn, producto_id)
    
    try:
        query = "DELETE FROM producto WHERE id = $1;"
        await conn.execute(query, producto_id)
    except asyncpg.exceptions.ForeignKeyViolationError:
        # Por si el producto está vinculado a alguna venta o compra (FK en tablas detalle)
        raise BadRequestException(detail="No se puede eliminar el producto porque tiene movimientos (ventas/compras) asociados.")
    except Exception as e:
        raise DatabaseException(f"Error al eliminar el producto: {str(e)}")

