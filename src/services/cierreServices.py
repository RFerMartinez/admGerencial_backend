from asyncpg import Connection
from datetime import date, datetime
from schemas.cierreSchema import CierreCreate
from utils.exceptions import BadRequestException, DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema


async def validar_periodo_abierto(conn: Connection, fecha) -> None:
    if isinstance(fecha, datetime):
        periodo = fecha.strftime('%Y-%m')
    elif isinstance(fecha, date):
        periodo = fecha.strftime('%Y-%m')
    else:
        periodo = str(fecha)[:7]
    cerrado = await conn.fetchval(
        "SELECT id FROM cierres_mensuales WHERE periodo = $1;", periodo
    )
    if cerrado:
        raise BadRequestException(
            detail=f"No se pueden registrar operaciones en el período {periodo} porque ya fue cerrado."
        )


async def obtener_historial(conn: Connection) -> list[dict]:
    rows = await conn.fetch("""
        SELECT id, periodo, fecha_cierre, total_ingresos, total_egresos, resultado, observaciones
        FROM cierres_mensuales
        ORDER BY periodo DESC;
    """)
    return [dict(r) for r in rows]


async def obtener_cierre_detalle(conn: Connection, cierre_id: int) -> dict:
    cierre = await conn.fetchrow("""
        SELECT id, periodo, fecha_cierre, asiento_id, total_ingresos, total_egresos, resultado, observaciones
        FROM cierres_mensuales WHERE id = $1;
    """, cierre_id)
    if not cierre:
        raise BadRequestException(detail="Cierre no encontrado.")

    detalles = await conn.fetch("""
        SELECT ad.cuenta_id, c.codigo, c.nombre, c.tipo, ad.debe, ad.haber
        FROM asientos_detalle ad
        JOIN cuentas c ON ad.cuenta_id = c.id
        WHERE ad.asiento_id = $1
        ORDER BY c.tipo, c.codigo;
    """, cierre['asiento_id'])

    return {
        **dict(cierre),
        "detalles": [dict(d) for d in detalles]
    }


async def preview_cierre(conn: Connection, periodo: str) -> dict:
    existente = await conn.fetchval(
        "SELECT id FROM cierres_mensuales WHERE periodo = $1;", periodo
    )
    if existente:
        raise BadRequestException(detail=f"El período {periodo} ya fue cerrado.")

    partes = periodo.split('-')
    fecha_inicio = date(int(partes[0]), int(partes[1]), 1)

    ingresos = await conn.fetch("""
        SELECT c.id as cuenta_id, c.codigo as cuenta_codigo, c.nombre as cuenta_nombre,
               COALESCE(SUM(ad.haber), 0) - COALESCE(SUM(ad.debe), 0) as saldo
        FROM cuentas c
        JOIN asientos_detalle ad ON c.id = ad.cuenta_id
        JOIN asientos a ON ad.asiento_id = a.id
        WHERE c.tipo = 'Ingreso'
          AND a.fecha >= $1
          AND a.fecha < ($1 + INTERVAL '1 month')
        GROUP BY c.id, c.codigo, c.nombre
        HAVING COALESCE(SUM(ad.haber), 0) - COALESCE(SUM(ad.debe), 0) != 0
        ORDER BY c.codigo;
    """, fecha_inicio)

    egresos = await conn.fetch("""
        SELECT c.id as cuenta_id, c.codigo as cuenta_codigo, c.nombre as cuenta_nombre,
               COALESCE(SUM(ad.debe), 0) - COALESCE(SUM(ad.haber), 0) as saldo
        FROM cuentas c
        JOIN asientos_detalle ad ON c.id = ad.cuenta_id
        JOIN asientos a ON ad.asiento_id = a.id
        WHERE c.tipo = 'Egreso'
          AND a.fecha >= $1
          AND a.fecha < ($1 + INTERVAL '1 month')
        GROUP BY c.id, c.codigo, c.nombre
        HAVING COALESCE(SUM(ad.debe), 0) - COALESCE(SUM(ad.haber), 0) != 0
        ORDER BY c.codigo;
    """, fecha_inicio)

    ingresos_list = [dict(r) for r in ingresos]
    egresos_list = [dict(r) for r in egresos]
    total_ing = sum(float(r['saldo']) for r in ingresos_list)
    total_egr = sum(float(r['saldo']) for r in egresos_list)

    return {
        "periodo": periodo,
        "ingresos": ingresos_list,
        "egresos": egresos_list,
        "total_ingresos": total_ing,
        "total_egresos": total_egr,
        "resultado": total_ing - total_egr
    }


async def ejecutar_cierre(conn: Connection, data: CierreCreate) -> dict:
    async with conn.transaction():
        existente = await conn.fetchval(
            "SELECT id FROM cierres_mensuales WHERE periodo = $1;", data.periodo
        )
        if existente:
            raise BadRequestException(detail=f"El período {data.periodo} ya fue cerrado.")

        preview = await preview_cierre(conn, data.periodo)

        if preview['total_ingresos'] == 0 and preview['total_egresos'] == 0:
            raise BadRequestException(detail=f"No hay movimientos de resultado en el período {data.periodo}.")

        config = await resolver_cuentas_sistema(conn, ['RESULTADO_EJERCICIO'])
        cuenta_resultado_id = config['RESULTADO_EJERCICIO']

        from datetime import timedelta
        partes = data.periodo.split('-')
        anio = int(partes[0])
        mes = int(partes[1])
        if mes == 12:
            ultimo_dia = date(anio, 12, 31)
        else:
            ultimo_dia = date(anio, mes + 1, 1) - timedelta(days=1)

        descripcion = f"Cierre mensual {data.periodo} - Refundición de cuentas de resultado"
        fecha_cierre_ts = datetime.combine(ultimo_dia, datetime.now().time())
        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            fecha_cierre_ts, descripcion
        )

        renglones = []

        for ing in preview['ingresos']:
            renglones.append((asiento_id, ing['cuenta_id'], float(ing['saldo']), 0.00))

        for egr in preview['egresos']:
            renglones.append((asiento_id, egr['cuenta_id'], 0.00, float(egr['saldo'])))

        resultado = preview['resultado']
        if resultado >= 0:
            renglones.append((asiento_id, cuenta_resultado_id, 0.00, resultado))
        else:
            renglones.append((asiento_id, cuenta_resultado_id, abs(resultado), 0.00))

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber)
            VALUES ($1, $2, $3, $4);
        """, renglones)

        cierre_id = await conn.fetchval("""
            INSERT INTO cierres_mensuales (periodo, fecha_cierre, asiento_id, total_ingresos, total_egresos, resultado, observaciones)
            VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id;
        """,
            data.periodo, ultimo_dia, asiento_id,
            preview['total_ingresos'], preview['total_egresos'], resultado,
            data.observaciones
        )

        return {
            "id": cierre_id,
            "periodo": data.periodo,
            "fecha_cierre": ultimo_dia,
            "asiento_id": asiento_id,
            "total_ingresos": preview['total_ingresos'],
            "total_egresos": preview['total_egresos'],
            "resultado": resultado,
            "observaciones": data.observaciones
        }
