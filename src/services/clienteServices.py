from asyncpg import Connection
from schemas.clienteSchema import ClienteCreate, ClienteBase
from typing import List
from utils.exceptions import NotFoundException

async def obtener_todos(conn: Connection, solo_activos: bool = True) -> List[dict]:
    query = "SELECT cuit, razon_social, domicilio_fiscal, condicion_iva, telefono, activo FROM clientes"
    if solo_activos:
        query += " WHERE activo = true"
    query += ";"
    records = await conn.fetch(query)
    return [dict(record) for record in records]

async def crear_cliente(conn: Connection, cliente: ClienteCreate) -> dict:
    query = """
        INSERT INTO clientes (cuit, razon_social, domicilio_fiscal, condicion_iva, telefono)
        VALUES ($1, $2, $3, $4, $5)
        RETURNING *;
    """
    record = await conn.fetchrow(
        query,
        cliente.cuit,
        cliente.razon_social,
        cliente.domicilio_fiscal,
        cliente.condicion_iva,
        cliente.telefono
    )
    return dict(record)

async def actualizar_cliente(conn: Connection, cuit: str, cliente: ClienteBase) -> dict:
    record = await conn.fetchrow(
        """
        UPDATE clientes SET razon_social = $1, domicilio_fiscal = $2, condicion_iva = $3, telefono = $4
        WHERE cuit = $5
        RETURNING cuit, razon_social, domicilio_fiscal, condicion_iva, telefono, activo;
        """,
        cliente.razon_social, cliente.domicilio_fiscal, cliente.condicion_iva, cliente.telefono, cuit
    )
    if not record:
        raise NotFoundException(detail=f"El cliente con CUIT {cuit} no existe.")
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

async def cambiar_estado(conn: Connection, cuit: str, activo: bool) -> dict:
    record = await conn.fetchrow(
        "UPDATE clientes SET activo = $1 WHERE cuit = $2 RETURNING cuit, razon_social, domicilio_fiscal, condicion_iva, telefono, activo;",
        activo, cuit
    )
    if not record:
        raise NotFoundException(detail=f"El cliente con CUIT {cuit} no existe.")
    return dict(record)
