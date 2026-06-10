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

async def obtener_libro_mayor(conn: Connection) -> list[dict]:
    try:
        # Consulta SQL base para extraer los renglones ordenados cronológicamente
        query = """
            SELECT
                c.id AS cuenta_id,
                c.codigo AS cuenta_codigo,
                c.nombre AS cuenta_nombre,
                c.tipo AS cuenta_tipo,
                a.fecha,
                ad.asiento_id,
                a.descripcion,
                ad.debe,
                ad.haber
            FROM asientos_detalle ad
            JOIN asientos a ON ad.asiento_id = a.id
            JOIN cuentas c ON ad.cuenta_id = c.id
            ORDER BY c.id ASC, a.fecha ASC, ad.id ASC;
        """
        
        records = await conn.fetch(query)
        
        mayor_agrupado = {}
        
        for record in records:
            c_id = record['cuenta_id']
            
            # Inicializar la cuenta contable en el diccionario si es el primer renglón que aparece
            if c_id not in mayor_agrupado:
                mayor_agrupado[c_id] = {
                    "cuenta_id": c_id,
                    "cuenta_codigo": record['cuenta_codigo'],
                    "cuenta_nombre": record['cuenta_nombre'],
                    "cuenta_tipo": record['cuenta_tipo'],
                    "saldo_final": 0.0,
                    "movimientos": [],
                    "_saldo_corrido": 0.0  # Variable temporal interna para el acumulador
                }
                
            account = mayor_agrupado[c_id]
            debe = float(record['debe'])
            haber = float(record['haber'])
            
            # Cálculo del saldo acumulado respetando la naturaleza contable de la cuenta
            # Activos y Egresos aumentan por el Debe, disminuyen por el Haber.
            # Pasivos, Patrimonios e Ingresos aumentan por el Haber, disminuyen por el Debe.
            if account["cuenta_tipo"] in ["Activo", "Egreso"]:
                account["_saldo_corrido"] += (debe - haber)
            else:
                account["_saldo_corrido"] += (haber - debe)
                
            # Añadir la línea de movimiento estructurada
            account["movimientos"].append({
                "fecha": record['fecha'],
                "asiento_id": record['asiento_id'],
                "descripcion": record['descripcion'],
                "debe": debe,
                "haber": haber,
                "saldo_acumulado": account["_saldo_corrido"]
            })
            
        # Limpieza de variables auxiliares y asignación del saldo final a la cabecera
        resultado_final = []
        for account in mayor_agrupado.values():
            account["saldo_final"] = account["_saldo_corrido"]
            del account["_saldo_corrido"]
            del account["cuenta_tipo"]  # Lo removemos para que coincida con el JSON del front
            resultado_final.append(account)
            
        return resultado_final

    except Exception as e:
        raise DatabaseException(f"Error al procesar el reporte del Libro Mayor: {str(e)}")

