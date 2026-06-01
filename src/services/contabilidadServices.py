# src/services/contabilidadServices.py
import asyncpg
from asyncpg import Connection
from utils.exceptions import DatabaseException

async def obtener_libro_diario(conn: Connection) -> list[dict]:
    try:
        # La consulta exacta requerida por la arquitectura
        query = """
            SELECT
                a.id AS nro_asiento,
                a.fecha,
                a.descripcion,
                c.codigo AS cuenta_codigo,
                c.nombre AS cuenta_nombre,
                ad.debe,
                ad.haber
            FROM asientos a
            JOIN asientos_detalle ad ON a.id = ad.asiento_id
            JOIN cuentas c ON ad.cuenta_id = c.id
            ORDER BY a.fecha DESC, a.id DESC, ad.debe DESC;
        """
        
        records = await conn.fetch(query)
        
        # Agrupamiento lógico en memoria
        asientos_agrupados = {}
        
        for record in records:
            nro = record['nro_asiento']
            
            # Si el asiento no existe en nuestro diccionario, lo inicializamos
            if nro not in asientos_agrupados:
                asientos_agrupados[nro] = {
                    "nro_asiento": nro,
                    "fecha": record['fecha'],
                    "descripcion": record['descripcion'],
                    "detalles": [],
                    "total_debe": 0.0,
                    "total_haber": 0.0
                }
            
            # Agregamos el renglón (detalle)
            debe = float(record['debe'])
            haber = float(record['haber'])
            
            asientos_agrupados[nro]["detalles"].append({
                "cuenta_codigo": record['cuenta_codigo'],
                "cuenta_nombre": record['cuenta_nombre'],
                "debe": debe,
                "haber": haber
            })
            
            # Sumamos los totales dinámicamente
            asientos_agrupados[nro]["total_debe"] += debe
            asientos_agrupados[nro]["total_haber"] += haber

        # Devolvemos solo la lista de valores ya agrupados y totalizados
        return list(asientos_agrupados.values())

    except Exception as e:
        raise DatabaseException(f"Error al consultar o procesar el Libro Diario: {str(e)}")

