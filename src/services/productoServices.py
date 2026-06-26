# src/services/productoServices.py
import asyncpg
from asyncpg import Connection
from schemas.productoSchema import ProductoCreate, ProductoUpdate
from utils.exceptions import NotFoundException, BadRequestException, DatabaseException


async def get_all_productos(conn: Connection) -> list[dict]:
    try:
        query = "SELECT id, nombre, precio, costo, stock, stock_minimo, tipo FROM producto ORDER BY id ASC;"
        records = await conn.fetch(query)
        return [dict(record) for record in records]
    except Exception as e:
        raise DatabaseException(f"Error al listar productos: {str(e)}")


async def get_producto_by_id(conn: Connection, producto_id: int) -> dict:
    query = "SELECT id, nombre, precio, costo, stock, stock_minimo, tipo FROM producto WHERE id = $1;"
    record = await conn.fetchrow(query, producto_id)
    if not record:
        raise NotFoundException(detail=f"El producto con ID {producto_id} no fue encontrado.")
    return dict(record)


async def create_producto(conn: Connection, producto: ProductoCreate) -> dict:
    query = """
        INSERT INTO producto (nombre, tipo, precio, costo, stock, stock_minimo)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id, nombre, precio, costo, stock, stock_minimo, tipo;
    """
    try:
        record = await conn.fetchrow(
            query, producto.nombre, producto.tipo, producto.precio,
            producto.costo, producto.stock, producto.stock_minimo
        )
        return dict(record)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail=f"La categoría '{producto.tipo}' no existe en el sistema.")
    except Exception as e:
        raise DatabaseException(f"Error al crear el producto: {str(e)}")


async def update_producto(conn: Connection, producto_id: int, data_update: ProductoUpdate) -> dict:
    producto_actual = await get_producto_by_id(conn, producto_id)

    nombre = data_update.nombre if data_update.nombre is not None else producto_actual["nombre"]
    tipo = data_update.tipo if data_update.tipo is not None else producto_actual["tipo"]
    precio = data_update.precio if data_update.precio is not None else producto_actual["precio"]
    costo = data_update.costo if data_update.costo is not None else producto_actual["costo"]
    stock = data_update.stock if data_update.stock is not None else producto_actual["stock"]
    stock_minimo = data_update.stock_minimo if data_update.stock_minimo is not None else producto_actual["stock_minimo"]

    query = """
        UPDATE producto
        SET nombre = $1, tipo = $2, precio = $3, costo = $4, stock = $5, stock_minimo = $6
        WHERE id = $7
        RETURNING id, nombre, precio, costo, stock, stock_minimo, tipo;
    """
    try:
        record = await conn.fetchrow(query, nombre, tipo, precio, costo, stock, stock_minimo, producto_id)
        return dict(record)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail=f"La categoría '{tipo}' no existe en el sistema.")
    except Exception as e:
        raise DatabaseException(f"Error al actualizar el producto: {str(e)}")


async def delete_producto(conn: Connection, producto_id: int) -> None:
    await get_producto_by_id(conn, producto_id)
    try:
        await conn.execute("DELETE FROM producto WHERE id = $1;", producto_id)
    except asyncpg.exceptions.ForeignKeyViolationError:
        raise BadRequestException(detail="No se puede eliminar el producto porque tiene movimientos asociados.")
    except Exception as e:
        raise DatabaseException(f"Error al eliminar el producto: {str(e)}")


async def get_alertas_stock(conn: Connection) -> list[dict]:
    query = """
        SELECT id, nombre, stock, stock_minimo, tipo
        FROM producto
        WHERE stock <= stock_minimo
        ORDER BY stock ASC, nombre ASC;
    """
    records = await conn.fetch(query)
    resultado = []
    for r in records:
        nivel = 'critico' if r['stock'] == 0 else 'bajo'
        resultado.append({
            "id": r['id'],
            "nombre": r['nombre'],
            "stock": r['stock'],
            "stock_minimo": r['stock_minimo'],
            "tipo": r['tipo'],
            "nivel": nivel
        })
    return resultado
