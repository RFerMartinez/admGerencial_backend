# src/services/productoServices.py
from asyncpg import Connection
from schemas.productoSchema import ProductoCreate, ProductoUpdate
from utils.exceptions import APIException

async def get_all_productos(conn: Connection) -> list[dict]:
    query = "SELECT * FROM producto ORDER BY id ASC;"
    records = await conn.fetch(query)
    # Convertimos los records de asyncpg a diccionarios estándar de Python
    return [dict(record) for record in records]

async def get_producto_by_id(conn: Connection, producto_id: int) -> dict:
    query = "SELECT * FROM producto WHERE id = $1;"
    record = await conn.fetchrow(query, producto_id)
    
    if not record:
        raise APIException(status_code=404, message=f"El producto con ID {producto_id} no fue encontrado.")
    
    return dict(record)

async def create_producto(conn: Connection, producto: ProductoCreate) -> dict:
    query = """
        INSERT INTO producto (nombre, tipo, precio, stock) 
        VALUES ($1, $2, $3, $4) 
        RETURNING *;
    """
    record = await conn.fetchrow(
        query, 
        producto.nombre, 
        producto.tipo, 
        producto.precio, 
        producto.stock
    )
    return dict(record)

async def update_producto(conn: Connection, producto_id: int, data_update: ProductoUpdate) -> dict:
    # 1. Verificar si existe
    producto_actual = await get_producto_by_id(conn, producto_id)
    
    # 2. Actualizar solo los campos que fueron enviados
    nombre = data_update.nombre if data_update.nombre is not None else producto_actual["nombre"]
    tipo = data_update.tipo if data_update.tipo is not None else producto_actual["tipo"]
    precio = data_update.precio if data_update.precio is not None else producto_actual["precio"]
    stock = data_update.stock if data_update.stock is not None else producto_actual["stock"]

    query = """
        UPDATE producto 
        SET nombre = $1, tipo = $2, precio = $3, stock = $4 
        WHERE id = $5 
        RETURNING *;
    """
    record = await conn.fetchrow(query, nombre, tipo, precio, stock, producto_id)
    return dict(record)

async def delete_producto(conn: Connection, producto_id: int) -> None:
    # Verificamos si existe antes de borrar
    await get_producto_by_id(conn, producto_id)
    
    query = "DELETE FROM producto WHERE id = $1;"
    await conn.execute(query, producto_id)

