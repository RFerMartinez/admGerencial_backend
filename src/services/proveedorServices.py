# src/services/proveedorServices.py
import asyncpg
from asyncpg import Connection
from schemas.proveedorSchema import PagoProveedorCreate
from utils.exceptions import NotFoundException, DatabaseException

async def obtener_deudas_activas(conn: Connection) -> list[dict]:
    # Lógica Contable: Pasivo aumenta por el Haber y disminuye por el Debe.
    # Filtramos por las cuentas de tipo "Pasivo" cuyo código empiece con "21" (Deudas comerciales/Proveedores)
    query = """
        SELECT 
            c.id AS cuenta_id, 
            c.codigo AS cuenta_codigo, 
            c.nombre AS proveedor_cuenta, 
            (SUM(ad.haber) - SUM(ad.debe)) AS saldo_pendiente
        FROM cuentas c
        JOIN asientos_detalle ad ON c.id = ad.cuenta_id
        WHERE c.tipo = 'Pasivo' AND c.codigo LIKE '21%'
        GROUP BY c.id, c.codigo, c.nombre
        HAVING (SUM(ad.haber) - SUM(ad.debe)) > 0
        ORDER BY saldo_pendiente DESC;
    """
    try:
        records = await conn.fetch(query)
        return [dict(record) for record in records]
    except Exception as e:
        raise DatabaseException(f"Error al calcular las deudas activas: {str(e)}")


async def registrar_pago(conn: Connection, pago_data: PagoProveedorCreate) -> dict:
    async with conn.transaction():
        # 1. Verificar la cuenta pasiva del proveedor
        cuenta_prov = await conn.fetchrow(
            "SELECT id FROM cuentas WHERE id = $1 AND tipo = 'Pasivo';", 
            pago_data.cuenta_proveedor_id
        )
        if not cuenta_prov:
            raise NotFoundException(detail=f"La cuenta con ID {pago_data.cuenta_proveedor_id} no existe o no es de tipo Pasivo.")

        # 2. Mapeo de cuenta de salida
        codigo_salida = '110001' if pago_data.metodo_pago == 'Efectivo' else '110003'
        cuenta_salida = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", codigo_salida)
        if not cuenta_salida:
            raise DatabaseException(detail=f"Falla contable: No se encontró la cuenta de salida ({codigo_salida}).")
        
        cuenta_salida_id = cuenta_salida['id']

        # 3. Asiento contable
        descripcion = pago_data.observaciones.strip() if pago_data.observaciones else f"Pago s/ {pago_data.tipo_comprobante} {pago_data.nro_comprobante_recibido}"

        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        asiento_id = await conn.fetchval(query_asiento, pago_data.fecha, descripcion)

        renglones_contables = [
            (asiento_id, pago_data.cuenta_proveedor_id, pago_data.monto_pagado, 0.00),
            (asiento_id, cuenta_salida_id, 0.00, pago_data.monto_pagado)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) 
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        # 4. Inserción en documentos_contables
        entidad_nombre = await conn.fetchval(
            "SELECT nombre FROM cuentas WHERE id = $1;", 
            pago_data.cuenta_proveedor_id
        )

        await conn.execute("""
            INSERT INTO documentos_contables (
                tipo_operacion, fecha_emision, tipo_comprobante, nro_comprobante,
                entidad_nombre, total, asiento_id, comprobante_padre_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
        """,
            'Pago',
            pago_data.fecha,
            pago_data.tipo_comprobante,
            pago_data.nro_comprobante_recibido,
            entidad_nombre,
            pago_data.monto_pagado,
            asiento_id,
            pago_data.comprobante_padre_id
        )

        return {"asiento_id": asiento_id}
    async with conn.transaction():
        # 1. Verificar que la cuenta de proveedor exista y sea realmente un Pasivo
        cuenta_prov = await conn.fetchrow(
            "SELECT id FROM cuentas WHERE id = $1 AND tipo = 'Pasivo';", 
            pago_data.cuenta_proveedor_id
        )
        if not cuenta_prov:
            raise NotFoundException(detail=f"La cuenta con ID {pago_data.cuenta_proveedor_id} no existe o no es de tipo Pasivo.")

        # 2. Mapeo de cuenta de salida (Caja o Banco)
        codigo_salida = '110001' if pago_data.metodo_pago == 'Efectivo' else '110003'
        cuenta_salida = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", codigo_salida)
        if not cuenta_salida:
            raise DatabaseException(detail=f"Falla contable: No se encontró la cuenta de salida ({codigo_salida}).")
        
        cuenta_salida_id = cuenta_salida['id']

        # 3. Procesar las observaciones
        descripcion = pago_data.observaciones.strip() if pago_data.observaciones else "Pago a cuenta proveedor"

        # 4. PASO B: Cabecera del asiento
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        asiento_id = await conn.fetchval(query_asiento, pago_data.fecha, descripcion)

        # 5. PASO C: Partida Doble
        renglones_contables = [
            # Renglón 1: Disminuye la Deuda -> Pasivo Baja (Debe)
            (asiento_id, pago_data.cuenta_proveedor_id, pago_data.monto_pagado, 0.00),
            # Renglón 2: Salida de Dinero -> Activo Baja (Haber)
            (asiento_id, cuenta_salida_id, 0.00, pago_data.monto_pagado)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) 
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        return {"asiento_id": asiento_id}

