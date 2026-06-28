# src/services/contabilidadServices.py
from asyncpg import Connection
from datetime import date, datetime, time
from typing import Optional
from utils.exceptions import DatabaseException
from schemas.contabilidadSchema import AsientoManualCreate
from services.cierreServices import validar_periodo_abierto


def _build_fecha_filter(periodo: Optional[str], fecha_desde: Optional[str], fecha_hasta: Optional[str]):
    conditions = []
    params = []
    idx = 1

    if periodo:
        partes = periodo.split('-')
        f_inicio = date(int(partes[0]), int(partes[1]), 1)
        conditions.append(f"a.fecha >= ${idx}::timestamp")
        params.append(f_inicio)
        idx += 1
        if int(partes[1]) == 12:
            f_fin = date(int(partes[0]) + 1, 1, 1)
        else:
            f_fin = date(int(partes[0]), int(partes[1]) + 1, 1)
        conditions.append(f"a.fecha < ${idx}::timestamp")
        params.append(f_fin)
        idx += 1
    else:
        if fecha_desde:
            conditions.append(f"a.fecha >= ${idx}::timestamp")
            params.append(date.fromisoformat(fecha_desde))
            idx += 1
        if fecha_hasta:
            conditions.append(f"a.fecha < (${idx}::date + 1)::timestamp")
            params.append(date.fromisoformat(fecha_hasta))
            idx += 1

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    return where_clause, params


async def obtener_libro_diario(conn: Connection, periodo: Optional[str] = None, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> list[dict]:
    try:
        where_clause, params = _build_fecha_filter(periodo, fecha_desde, fecha_hasta)

        query = f"""
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
            {where_clause}
            ORDER BY a.fecha DESC, a.id DESC, ad.debe DESC;
        """

        records = await conn.fetch(query, *params)

        asientos_agrupados = {}
        for record in records:
            nro = record['nro_asiento']
            if nro not in asientos_agrupados:
                asientos_agrupados[nro] = {
                    "nro_asiento": nro,
                    "fecha": record['fecha'],
                    "descripcion": record['descripcion'],
                    "detalles": [],
                    "total_debe": 0.0,
                    "total_haber": 0.0
                }

            debe = float(record['debe'])
            haber = float(record['haber'])

            asientos_agrupados[nro]["detalles"].append({
                "cuenta_codigo": record['cuenta_codigo'],
                "cuenta_nombre": record['cuenta_nombre'],
                "debe": debe,
                "haber": haber
            })

            asientos_agrupados[nro]["total_debe"] += debe
            asientos_agrupados[nro]["total_haber"] += haber

        return list(asientos_agrupados.values())

    except Exception as e:
        raise DatabaseException(f"Error al consultar el Libro Diario: {str(e)}")


async def obtener_libro_mayor(conn: Connection, periodo: Optional[str] = None, fecha_desde: Optional[str] = None, fecha_hasta: Optional[str] = None) -> list[dict]:
    try:
        where_clause, params = _build_fecha_filter(periodo, fecha_desde, fecha_hasta)

        query = f"""
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
            {where_clause}
            ORDER BY c.id ASC, a.fecha ASC, ad.id ASC;
        """

        records = await conn.fetch(query, *params)
        mayor_agrupado = {}

        for record in records:
            c_id = record['cuenta_id']
            tipo_cuenta = record['cuenta_tipo']

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
                    "_saldo_corrido": 0.0
                }

            account = mayor_agrupado[c_id]
            debe = float(record['debe'])
            haber = float(record['haber'])

            if account["_naturaleza"] == "Deudora":
                account["_saldo_corrido"] += (debe - haber)
            else:
                account["_saldo_corrido"] += (haber - debe)

            account["movimientos"].append({
                "fecha": record['fecha'],
                "asiento_id": record['asiento_id'],
                "descripcion": record['descripcion'],
                "debe": debe,
                "haber": haber,
                "saldo_acumulado": account["_saldo_corrido"]
            })

        resultado_final = []
        for account in mayor_agrupado.values():
            saldo_acumulado = account["_saldo_corrido"]
            naturaleza = account["_naturaleza"]

            if saldo_acumulado > 0:
                tipo_saldo = "Deudor" if naturaleza == "Deudora" else "Acreedor"
                valor_saldo = saldo_acumulado
            elif saldo_acumulado < 0:
                tipo_saldo = "Acreedor" if naturaleza == "Deudora" else "Deudor"
                valor_saldo = abs(saldo_acumulado)
            else:
                tipo_saldo = "Saldada"
                valor_saldo = 0.0

            account["saldo_final"] = {"tipo": tipo_saldo, "valor": valor_saldo}
            del account["_saldo_corrido"]
            del account["_naturaleza"]
            resultado_final.append(account)

        return resultado_final

    except Exception as e:
        raise DatabaseException(f"Error al procesar el Libro Mayor: {str(e)}")


async def registrar_asiento_manual(conn: Connection, asiento_data: AsientoManualCreate) -> dict:
    if len(asiento_data.detalles) < 2:
        raise DatabaseException("El asiento manual requiere un mínimo de 2 cuentas para aplicar la partida doble.")

    total_debe = round(sum(detalle.debe for detalle in asiento_data.detalles), 2)
    total_haber = round(sum(detalle.haber for detalle in asiento_data.detalles), 2)

    if total_debe <= 0:
        raise DatabaseException("El total del asiento debe ser mayor a 0.")

    if total_debe != total_haber:
        raise DatabaseException(f"Error de Partida Doble: El Debe ({total_debe}) no coincide con el Haber ({total_haber}).")

    try:
        async with conn.transaction():
            await validar_periodo_abierto(conn, asiento_data.fecha)

            fecha_con_hora = datetime.combine(asiento_data.fecha, datetime.now().time())
            asiento_id = await conn.fetchval("""
                INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;
            """, fecha_con_hora, asiento_data.descripcion)

            renglones_contables = [
                (asiento_id, detalle.cuenta_id, detalle.debe, detalle.haber)
                for detalle in asiento_data.detalles
            ]

            await conn.executemany("""
                INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) VALUES ($1, $2, $3, $4);
            """, renglones_contables)

        return {"mensaje": "Asiento registrado con éxito", "asiento_id": asiento_id}

    except DatabaseException:
        raise
    except Exception as e:
        raise DatabaseException(f"Fallo al registrar el asiento manual: {str(e)}")


async def obtener_balance(conn: Connection, fecha: Optional[str] = None) -> dict:
    try:
        fecha_corte = date.fromisoformat(fecha) if fecha else date.today()
        ts_corte = datetime.combine(fecha_corte, datetime.max.time())

        query = """
            SELECT
                c.id, c.codigo, c.nombre, c.tipo,
                SUM(ad.debe) as total_debe,
                SUM(ad.haber) as total_haber
            FROM asientos_detalle ad
            JOIN asientos a ON ad.asiento_id = a.id
            JOIN cuentas c ON ad.cuenta_id = c.id
            WHERE a.fecha <= $1
            GROUP BY c.id, c.codigo, c.nombre, c.tipo
            ORDER BY c.codigo;
        """
        records = await conn.fetch(query, ts_corte)

        activo = []
        pasivo = []
        patrimonio = []
        total_ingresos = 0.0
        total_egresos = 0.0

        for r in records:
            debe = float(r['total_debe'])
            haber = float(r['total_haber'])
            tipo = r['tipo']

            if tipo == 'Activo':
                saldo = debe - haber
                if saldo != 0:
                    activo.append({"cuenta_id": r['id'], "codigo": r['codigo'], "nombre": r['nombre'], "saldo": saldo})
            elif tipo == 'Pasivo':
                saldo = haber - debe
                if saldo != 0:
                    pasivo.append({"cuenta_id": r['id'], "codigo": r['codigo'], "nombre": r['nombre'], "saldo": saldo})
            elif tipo == 'Patrimonio Neto':
                saldo = haber - debe
                if saldo != 0:
                    patrimonio.append({"cuenta_id": r['id'], "codigo": r['codigo'], "nombre": r['nombre'], "saldo": saldo})
            elif tipo == 'Ingreso':
                total_ingresos += (haber - debe)
            elif tipo == 'Egreso':
                total_egresos += (debe - haber)

        resultado_ejercicio = total_ingresos - total_egresos
        total_activo = sum(c['saldo'] for c in activo)
        total_pasivo = sum(c['saldo'] for c in pasivo)
        total_patrimonio = sum(c['saldo'] for c in patrimonio)
        total_pasivo_pn = total_pasivo + total_patrimonio + resultado_ejercicio

        return {
            "fecha_corte": str(fecha_corte),
            "activo": {"cuentas": activo, "total": round(total_activo, 2)},
            "pasivo": {"cuentas": pasivo, "total": round(total_pasivo, 2)},
            "patrimonio_neto": {
                "cuentas": patrimonio,
                "resultado_ejercicio": round(resultado_ejercicio, 2),
                "total": round(total_patrimonio + resultado_ejercicio, 2)
            },
            "total_pasivo_patrimonio": round(total_pasivo_pn, 2),
            "ecuacion_verificada": round(total_activo, 2) == round(total_pasivo_pn, 2)
        }

    except Exception as e:
        raise DatabaseException(f"Error al generar el Balance General: {str(e)}")
