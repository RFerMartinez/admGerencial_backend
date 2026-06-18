from asyncpg import Connection
from schemas.clienteSchema import ClienteCreate
from typing import List

async def obtener_todos(conn: Connection) -> List[dict]:
    query = "SELECT cuit, razon_social, domicilio_fiscal, condicion_iva FROM clientes;"
    records = await conn.fetch(query)
    return [dict(record) for record in records]

async def crear_cliente(conn: Connection, cliente: ClienteCreate) -> dict:
    query = """
        INSERT INTO clientes (cuit, razon_social, domicilio_fiscal, condicion_iva)
        VALUES ($1, $2, $3, $4)
        RETURNING *;
    """
    record = await conn.fetchrow(
        query, 
        cliente.cuit, 
        cliente.razon_social, 
        cliente.domicilio_fiscal, 
        cliente.condicion_iva
    )
    return dict(record)

async def obtener_o_crear_silencioso(conn: Connection, cuit: str, razon_social: str, domicilio: str, condicion_iva: str) -> None:
    """
    Inserta el cliente si no existe. Si el CUIT ya existe, lo ignora silenciosamente.
    """
    query = """
        INSERT INTO clientes (cuit, razon_social, domicilio_fiscal, condicion_iva)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (cuit) DO NOTHING;
    """
    await conn.execute(query, cuit, razon_social, domicilio, condicion_iva)