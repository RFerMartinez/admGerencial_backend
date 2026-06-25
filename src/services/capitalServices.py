# src/services/capitalServices.py
from asyncpg import Connection
from schemas.capitalSchema import CapitalInicialCreate
from utils.exceptions import DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema

async def registrar_capital_inicial(conn: Connection, capital_data: CapitalInicialCreate) -> dict:
    try:
        async with conn.transaction():

            monto_capital = capital_data.monto_caja + capital_data.monto_banco

            if monto_capital <= 0:
                raise ValueError("El capital total aportado debe ser mayor a cero.")

            config = await resolver_cuentas_sistema(conn, ['CAJA', 'BANCO', 'CAPITAL'])

            query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
            asiento_id = await conn.fetchval(query_asiento, capital_data.fecha, "Por inicio de actividades")

            renglones_contables = [
                (asiento_id, config['CAJA'], capital_data.monto_caja, 0.00),
                (asiento_id, config['BANCO'], capital_data.monto_banco, 0.00),
                (asiento_id, config['CAPITAL'], 0.00, monto_capital)
            ]

            await conn.executemany("""
                INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber)
                VALUES ($1, $2, $3, $4);
            """, renglones_contables)

            return {
                "asiento_id": asiento_id,
                "total_capital": monto_capital
            }

    except DatabaseException:
        raise
    except Exception as e:
        raise DatabaseException(f"Error al registrar el capital inicial: {str(e)}")

