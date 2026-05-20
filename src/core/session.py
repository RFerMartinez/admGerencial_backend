from asyncpg import create_pool, Pool, Connection
from typing import AsyncGenerator
from core.config import settings

# Variable global para el pool de conexiones
_db_pool: Pool | None = None

# Función asíncrona para crear un pool de conexiones a la base de datos
async def create_db_pool() -> Pool:
    return await create_pool(
        dsn=settings.DATABASE_URL.unicode_string(),
        min_size=5,
        max_size=15,
        timeout=30,
        command_timeout=60,
        max_inactive_connection_lifetime=300,
        server_settings={
            'search_path': 'public'
        }
    )

async def connect_to_db() -> None:
    global _db_pool
    _db_pool = await create_db_pool()

async def close_db_connection() -> None:
    global _db_pool
    if _db_pool:
        await _db_pool.close()

# Función de conexion a la DB para inyección de dependencias en tus rutas
async def get_db() -> AsyncGenerator[Connection, None]:
    if _db_pool is None:
        raise Exception("El pool de base de datos no está inicializado.")
        
    async with _db_pool.acquire() as conn:
        try:
            yield conn
        finally:
            pass