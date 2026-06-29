from asyncpg import Connection
from datetime import date, datetime
from services.cuentaSistemaServices import resolver_cuentas_sistema


async def obtener_dashboard(conn: Connection) -> dict:
    hoy = date.today()
    mes_actual = f"{hoy.year}-{hoy.month:02d}"
    if hoy.month == 1:
        mes_anterior = f"{hoy.year - 1}-12"
    else:
        mes_anterior = f"{hoy.year}-{hoy.month - 1:02d}"

    ts_inicio_mes = datetime(hoy.year, hoy.month, 1)
    if hoy.month == 1:
        ts_inicio_mes_ant = datetime(hoy.year - 1, 12, 1)
    else:
        ts_inicio_mes_ant = datetime(hoy.year, hoy.month - 1, 1)
    ts_ahora = datetime.combine(hoy, datetime.max.time())

    # --- KPIs del mes actual ---
    ventas_mes = await conn.fetchval("""
        SELECT COALESCE(SUM(v.total), 0) FROM ventas v
        JOIN asientos a ON v.asiento_id = a.id
        WHERE a.fecha >= $1 AND a.fecha <= $2
    """, ts_inicio_mes, ts_ahora) or 0

    ventas_mes_ant = await conn.fetchval("""
        SELECT COALESCE(SUM(v.total), 0) FROM ventas v
        JOIN asientos a ON v.asiento_id = a.id
        WHERE a.fecha >= $1 AND a.fecha < $2
    """, ts_inicio_mes_ant, ts_inicio_mes) or 0

    compras_mes = await conn.fetchval("""
        SELECT COALESCE(SUM(cm.total), 0) FROM compras_mercaderia cm
        JOIN asientos a ON cm.asiento_id = a.id
        WHERE a.fecha >= $1 AND a.fecha <= $2
    """, ts_inicio_mes, ts_ahora) or 0

    gastos_mes = await conn.fetchval("""
        SELECT COALESCE(SUM(g.monto), 0) FROM gastos g
        JOIN asientos a ON g.asiento_id = a.id
        WHERE a.fecha >= $1 AND a.fecha <= $2
    """, ts_inicio_mes, ts_ahora) or 0

    # Resultado del período (ingresos - egresos del mes)
    ingresos_mes = await conn.fetchval("""
        SELECT COALESCE(SUM(ad.haber) - SUM(ad.debe), 0)
        FROM asientos_detalle ad
        JOIN asientos a ON ad.asiento_id = a.id
        JOIN cuentas c ON ad.cuenta_id = c.id
        WHERE c.tipo = 'Ingreso' AND a.fecha >= $1 AND a.fecha <= $2
    """, ts_inicio_mes, ts_ahora) or 0

    egresos_mes = await conn.fetchval("""
        SELECT COALESCE(SUM(ad.debe) - SUM(ad.haber), 0)
        FROM asientos_detalle ad
        JOIN asientos a ON ad.asiento_id = a.id
        JOIN cuentas c ON ad.cuenta_id = c.id
        WHERE c.tipo = 'Egreso' AND a.fecha >= $1 AND a.fecha <= $2
    """, ts_inicio_mes, ts_ahora) or 0

    resultado_periodo = float(ingresos_mes) - float(egresos_mes)

    # --- Liquidez: Caja y Banco ---
    try:
        config = await resolver_cuentas_sistema(conn, ['CAJA', 'BANCO'])
        saldo_caja = await conn.fetchval("""
            SELECT COALESCE(SUM(ad.debe) - SUM(ad.haber), 0)
            FROM asientos_detalle ad
            JOIN asientos a ON ad.asiento_id = a.id
            WHERE ad.cuenta_id = $1 AND a.fecha <= $2
        """, config['CAJA'], ts_ahora) or 0

        saldo_banco = await conn.fetchval("""
            SELECT COALESCE(SUM(ad.debe) - SUM(ad.haber), 0)
            FROM asientos_detalle ad
            JOIN asientos a ON ad.asiento_id = a.id
            WHERE ad.cuenta_id = $1 AND a.fecha <= $2
        """, config['BANCO'], ts_ahora) or 0
    except Exception:
        saldo_caja = 0
        saldo_banco = 0

    # --- Deuda a proveedores ---
    deuda_total = await conn.fetchval("""
        SELECT COALESCE(SUM(sub.deuda), 0) FROM (
            SELECT COALESCE(SUM(d.total_deuda), 0) - COALESCE(pagos.total_pagado, 0) as deuda
            FROM proveedores p
            LEFT JOIN (
                SELECT proveedor_id, SUM(total_deuda) AS total_deuda FROM (
                    SELECT proveedor_id, SUM(total) AS total_deuda FROM compras_mercaderia WHERE proveedor_id IS NOT NULL GROUP BY proveedor_id
                    UNION ALL
                    SELECT proveedor_id, SUM(monto) AS total_deuda FROM gastos WHERE proveedor_id IS NOT NULL GROUP BY proveedor_id
                ) s GROUP BY proveedor_id
            ) d ON p.id = d.proveedor_id
            LEFT JOIN (
                SELECT proveedor_id, SUM(monto) AS total_pagado FROM pagos_proveedor GROUP BY proveedor_id
            ) pagos ON p.id = pagos.proveedor_id
            GROUP BY p.id, pagos.total_pagado
            HAVING COALESCE(SUM(d.total_deuda), 0) - COALESCE(pagos.total_pagado, 0) > 0
        ) sub
    """) or 0

    # --- Alertas de stock ---
    alertas_stock = await conn.fetch("""
        SELECT id, nombre, stock, stock_minimo
        FROM producto
        WHERE stock <= stock_minimo
        ORDER BY stock ASC, nombre ASC
        LIMIT 5;
    """)
    total_alertas = await conn.fetchval("""
        SELECT COUNT(*) FROM producto WHERE stock <= stock_minimo;
    """) or 0

    # --- Últimas 5 ventas ---
    ultimas_ventas = await conn.fetch("""
        SELECT v.id, v.fecha, v.total,
               dc.tipo_comprobante, dc.nro_comprobante
        FROM ventas v
        JOIN asientos a ON v.asiento_id = a.id
        JOIN documentos_contables dc ON dc.venta_id = v.id
        ORDER BY a.fecha DESC, v.id DESC
        LIMIT 5;
    """)

    # --- Último cierre ---
    ultimo_cierre = await conn.fetchrow("""
        SELECT periodo, fecha_cierre, resultado
        FROM cierres_mensuales
        ORDER BY periodo DESC LIMIT 1;
    """)

    # --- Ecuación patrimonial rápida ---
    saldos = await conn.fetch("""
        SELECT c.tipo, SUM(ad.debe) as total_debe, SUM(ad.haber) as total_haber
        FROM asientos_detalle ad
        JOIN asientos a ON ad.asiento_id = a.id
        JOIN cuentas c ON ad.cuenta_id = c.id
        WHERE a.fecha <= $1
        GROUP BY c.tipo;
    """, ts_ahora)

    total_activo = 0
    total_pasivo = 0
    total_pn = 0
    total_ing = 0
    total_egr = 0
    for s in saldos:
        d, h = float(s['total_debe']), float(s['total_haber'])
        if s['tipo'] == 'Activo': total_activo = d - h
        elif s['tipo'] == 'Pasivo': total_pasivo = h - d
        elif s['tipo'] == 'Patrimonio Neto': total_pn = h - d
        elif s['tipo'] == 'Ingreso': total_ing = h - d
        elif s['tipo'] == 'Egreso': total_egr = d - h

    resultado_acum = total_ing - total_egr

    # Variación ventas
    v_mes = float(ventas_mes)
    v_ant = float(ventas_mes_ant)
    if v_ant > 0:
        variacion_ventas = round(((v_mes - v_ant) / v_ant) * 100, 1)
    elif v_mes > 0:
        variacion_ventas = 100.0
    else:
        variacion_ventas = 0.0

    return {
        "kpis": {
            "ventas_mes": round(v_mes, 2),
            "ventas_mes_anterior": round(v_ant, 2),
            "variacion_ventas": variacion_ventas,
            "compras_mes": round(float(compras_mes), 2),
            "gastos_mes": round(float(gastos_mes), 2),
            "resultado_periodo": round(resultado_periodo, 2),
        },
        "liquidez": {
            "saldo_caja": round(float(saldo_caja), 2),
            "saldo_banco": round(float(saldo_banco), 2),
        },
        "deuda_proveedores": round(float(deuda_total), 2),
        "stock": {
            "total_alertas": total_alertas,
            "productos_criticos": [dict(r) for r in alertas_stock],
        },
        "ultimas_ventas": [
            {"id": r['id'], "fecha": r['fecha'], "total": float(r['total']),
             "tipo_comprobante": r['tipo_comprobante'], "nro_comprobante": r['nro_comprobante']}
            for r in ultimas_ventas
        ],
        "ultimo_cierre": {
            "periodo": ultimo_cierre['periodo'],
            "fecha_cierre": ultimo_cierre['fecha_cierre'],
            "resultado": float(ultimo_cierre['resultado']),
        } if ultimo_cierre else None,
        "ecuacion": {
            "activo": round(total_activo, 2),
            "pasivo": round(total_pasivo, 2),
            "patrimonio_neto": round(total_pn + resultado_acum, 2),
            "verificada": round(total_activo, 2) == round(total_pasivo + total_pn + resultado_acum, 2),
        }
    }
