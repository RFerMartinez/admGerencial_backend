# src/services/compraServices.py
from asyncpg import Connection
from datetime import datetime
from schemas.compraSchema import CompraCreate
from utils.exceptions import NotFoundException, DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema
from services.cierreServices import validar_periodo_abierto


async def procesar_compra(conn: Connection, compra_data: CompraCreate) -> dict:
    async with conn.transaction():

        await validar_periodo_abierto(conn, compra_data.fecha)

        # --- PREPARACIÓN Y VALIDACIÓN DE PRODUCTOS ---
        for item in compra_data.detalles:
            prod = await conn.fetchrow(
                "SELECT id FROM producto WHERE id = $1 FOR UPDATE;", item.producto_id
            )
            if not prod:
                raise NotFoundException(detail=f"El producto con ID {item.producto_id} no existe.")

        # --- ENRUTAMIENTO CONTABLE ---
        if compra_data.proveedor_id is not None:
            # Compra a crédito: validar proveedor + usar cuenta única PROVEEDORES
            prov = await conn.fetchrow(
                "SELECT id, nombre FROM proveedores WHERE id = $1;", compra_data.proveedor_id
            )
            if not prov:
                raise NotFoundException(detail=f"El proveedor con ID {compra_data.proveedor_id} no existe.")

            config = await resolver_cuentas_sistema(conn, ['MERCADERIAS', 'PROVEEDORES'])
            cuenta_haber_id = config['PROVEEDORES']
            entidad_nombre = prov['nombre']
        else:
            # Compra al contado
            if compra_data.metodo_pago == "Efectivo":
                rol_haber = 'CAJA'
            elif compra_data.metodo_pago in ["Transferencia", "Tarjeta"]:
                rol_haber = 'BANCO'
            else:
                raise DatabaseException("Método de pago inválido.")

            config = await resolver_cuentas_sistema(conn, [rol_haber, 'MERCADERIAS'])
            cuenta_haber_id = config[rol_haber]
            entidad_nombre = None

        cuenta_debe_id = config['MERCADERIAS']

        # --- PASO 1: ASIENTO CONTABLE ---
        descripcion_asiento = f"Compra s/ {compra_data.tipo_comprobante} {compra_data.nro_comprobante}"
        asiento_id = await conn.fetchval(
            "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;",
            datetime.now(), descripcion_asiento
        )

        # --- PASO 2: REGISTRO OPERATIVO Y DOCUMENTAL ---
        compra_id = await conn.fetchval("""
            INSERT INTO compras_mercaderia (fecha, total, asiento_id, proveedor_id)
            VALUES ($1, $2, $3, $4) RETURNING id;
        """, compra_data.fecha, compra_data.total, asiento_id, compra_data.proveedor_id)

        await conn.fetchval("""
            INSERT INTO documentos_contables (
                tipo_operacion, tipo_comprobante, nro_comprobante, fecha_emision, total, compra_id, entidad_nombre
            ) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id;
        """,
            'Compra',
            compra_data.tipo_comprobante,
            compra_data.nro_comprobante,
            compra_data.fecha,
            compra_data.total,
            compra_id,
            entidad_nombre
        )

        # --- PASO 3: INVENTARIO Y COSTOS ---
        for item in compra_data.detalles:
            await conn.execute("""
                INSERT INTO compras_detalle (compra_id, producto_id, cantidad, costo_unitario)
                VALUES ($1, $2, $3, $4);
            """, compra_id, item.producto_id, item.cantidad, item.costo_unitario)

            await conn.execute("""
                UPDATE producto SET stock = stock + $1, costo = $2 WHERE id = $3;
            """, item.cantidad, item.costo_unitario, item.producto_id)

        # --- PASO 4: PARTIDA DOBLE ---
        renglones_contables = [
            (asiento_id, cuenta_debe_id, compra_data.total, 0.00),
            (asiento_id, cuenta_haber_id, 0.00, compra_data.total)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber)
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        return {
            "id": compra_id,
            "fecha": compra_data.fecha,
            "total": compra_data.total,
            "asiento_id": asiento_id,
            "tipo_comprobante": compra_data.tipo_comprobante,
            "nro_comprobante": compra_data.nro_comprobante
        }
