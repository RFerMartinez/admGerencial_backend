# src/services/capitalServices.py
import asyncpg
from asyncpg import Connection
from schemas.capitalSchema import CapitalInicialCreate
from utils.exceptions import DatabaseException

async def registrar_capital_inicial(conn: Connection, capital_data: CapitalInicialCreate) -> dict:
    try:
        # El bloque transaccional asegura el db.commit() si todo sale bien 
        # y el db.rollback() si ocurre alguna excepción dentro del bloque.
        async with conn.transaction():
            
            # Cálculo del Capital
            monto_capital = capital_data.monto_caja + capital_data.monto_banco
            
            if monto_capital <= 0:
                raise ValueError("El capital total aportado debe ser mayor a cero.")

            # Búsqueda de IDs internos por código de cuenta para mantener integridad relacional
            cuentas_codigos = ['110001', '110003', '300001']
            cuentas_ids = {}
            
            for cod in cuentas_codigos:
                cuenta = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", cod)
                if not cuenta:
                    raise DatabaseException(detail=f"Falla contable: No se encontró la cuenta con código {cod}.")
                cuentas_ids[cod] = cuenta['id']

            # --- PASO A: Cabecera del asiento ---
            query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
            descripcion_fija = "Por inicio de actividades"
            asiento_id = await conn.fetchval(query_asiento, capital_data.fecha, descripcion_fija)

            # --- PASO B: Partida Doble (3 renglones estrictos) ---
            renglones_contables = [
                # Renglón 1: Ingreso a Caja (Debe)
                (asiento_id, cuentas_ids['110001'], capital_data.monto_caja, 0.00),
                
                # Renglón 2: Ingreso a Banco (Debe)
                (asiento_id, cuentas_ids['110003'], capital_data.monto_banco, 0.00),
                
                # Renglón 3: Reconocimiento del Capital (Haber)
                (asiento_id, cuentas_ids['300001'], 0.00, monto_capital)
            ]

            await conn.executemany("""
                INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) 
                VALUES ($1, $2, $3, $4);
            """, renglones_contables)

            return {
                "asiento_id": asiento_id,
                "total_capital": monto_capital
            }
            
    except Exception as e:
        # Si algo falla (ej. problemas de red, constraints SQL, o la validación <= 0),
        # se dispara el rollback internamente y luego capturamos el error para devolverlo limpio.
        raise DatabaseException(f"Error al registrar el capital inicial: {str(e)}")

