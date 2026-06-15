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
        # Consulta base para extraer los renglones ordenados cronológicamente
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
            tipo_cuenta = record['cuenta_tipo']
            
            # 1. Definición de la naturaleza de la cuenta según su tipo
            # Activos y Egresos aumentan por el Debe (Naturaleza Deudora)
            # Pasivos, Patrimonios e Ingresos aumentan por el Haber (Naturaleza Acreedora)
            if tipo_cuenta in ["Activo", "Egreso"]:
                naturaleza = "Deudora"
            else:
                naturaleza = "Acreedora"
                
            if c_id not in mayor_agrupado:
                mayor_agrupado[c_id] = {
                    "cuenta_id": c_id,
                    "cuenta_codigo": record['cuenta_codigo'],
                    "cuenta_nombre": record['cuenta_nombre'],
                    "_naturaleza": naturaleza,
                    "movimientos": [],
                    "_saldo_corrido": 0.0  # Acumulador temporal interno
                }
                
            account = mayor_agrupado[c_id]
            debe = float(record['debe'])
            haber = float(record['haber'])
            
            # 2. Cálculo del saldo parcial acumulado según la naturaleza
            if account["_naturaleza"] == "Deudora":
                account["_saldo_corrido"] += (debe - haber)
            else:
                account["_saldo_corrido"] += (haber - debe)
                
            # Añadir la línea del movimiento con el formato 'saldo_parcial'
            account["movimientos"].append({
                "fecha": record['fecha'],
                "asiento_id": record['asiento_id'],
                "descripcion": record['descripcion'],
                "debe": debe,
                "haber": haber,
                "saldo_parcial": account["_saldo_corrido"]
            })
            
        resultado_final = []
        for account in mayor_agrupado.values():
            saldo_acumulado = account["_saldo_corrido"]
            naturaleza = account["_naturaleza"]
            
            # 3. Clasificación final del saldo analizando si es consistente o excepcional
            if saldo_acumulado > 0:
                tipo_saldo = "Deudor" if naturaleza == "Deudora" else "Acreedor"
                valor_saldo = saldo_acumulado
            elif saldo_acumulado < 0:
                # Caso excepcional: Saldo negativo respecto a su naturaleza
                tipo_saldo = "Acreedor" if naturaleza == "Deudora" else "Deudor"
                valor_saldo = abs(saldo_acumulado)
            else:
                # Validación estricta de saldo cero
                tipo_saldo = "Saldada"
                valor_saldo = 0.0
                
            # Formatear la salida estructurada de acuerdo al nuevo esquema JSON
            account["saldo_final"] = {
                "tipo": tipo_saldo,
                "valor": valor_saldo
            }
            
            # Limpieza de metadatos privados auxiliares
            del account["_saldo_corrido"]
            del account["_naturaleza"]
            resultado_final.append(account)
            
        return resultado_final

    except Exception as e:
        raise DatabaseException(f"Error al procesar el reporte del Libro Mayor: {str(e)}")

