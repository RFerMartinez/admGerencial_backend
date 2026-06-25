# src/services/compraServices.py
from asyncpg import Connection
from schemas.compraSchema import CompraCreate
from utils.exceptions import NotFoundException, DatabaseException
from services.cuentaSistemaServices import resolver_cuentas_sistema

async def procesar_compra(conn: Connection, compra_data: CompraCreate) -> dict:
    async with conn.transaction():
        
        # --- PREPARACIÓN Y VALIDACIÓN DE PRODUCTOS ---
        for item in compra_data.detalles:
            prod = await conn.fetchrow("""
                SELECT id FROM producto WHERE id = $1 FOR UPDATE;
            """, item.producto_id)
            
            if not prod:
                raise NotFoundException(detail=f"El producto con ID {item.producto_id} no existe.")

        # --- ENRUTAMIENTO CONTABLE (HABER) ---
        cuenta_haber_id = None

        if compra_data.cuenta_proveedor_id is not None:
            cuenta_haber_id = compra_data.cuenta_proveedor_id
            cuenta_existe = await conn.fetchval("SELECT id FROM cuentas WHERE id = $1;", cuenta_haber_id)
            if not cuenta_existe:
                raise NotFoundException(detail=f"La cuenta contable con ID {cuenta_haber_id} no existe.")
            config = await resolver_cuentas_sistema(conn, ['MERCADERIAS'])
        else:
            if compra_data.metodo_pago == "Efectivo":
                rol_haber = 'CAJA'
            elif compra_data.metodo_pago in ["Transferencia", "Tarjeta"]:
                rol_haber = 'BANCO'
            else:
                raise DatabaseException("Método de pago inválido.")

            config = await resolver_cuentas_sistema(conn, [rol_haber, 'MERCADERIAS'])
            cuenta_haber_id = config[rol_haber]

        # --- ENRUTAMIENTO CONTABLE (DEBE) ---
        cuenta_debe_id = config['MERCADERIAS']

        # --- PASO 1: ASIENTO CONTABLE ---
        descripcion_asiento = f"Compra s/ {compra_data.tipo_comprobante} {compra_data.nro_comprobante}"
            
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        asiento_id = await conn.fetchval(query_asiento, compra_data.fecha, descripcion_asiento)

        # --- PASO 2: REGISTRO OPERATIVO Y DOCUMENTAL ---
        compra_id = await conn.fetchval("""
            INSERT INTO compras_mercaderia (fecha, total, asiento_id) 
            VALUES ($1, $2, $3) RETURNING id;
        """, compra_data.fecha, compra_data.total, asiento_id)

        # Inserción en la tabla central de documentos
        await conn.fetchval("""
            INSERT INTO documentos_contables (
                tipo_operacion, tipo_comprobante, nro_comprobante, fecha_emision, total, compra_id
            ) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id;
        """, 
            'Compra',
            compra_data.tipo_comprobante, 
            compra_data.nro_comprobante, 
            compra_data.fecha, 
            compra_data.total, 
            compra_id
        )

        # --- PASO 3: INVENTARIO Y COSTOS ---
        for item in compra_data.detalles:
            await conn.execute("""
                INSERT INTO compras_detalle (compra_id, producto_id, cantidad, costo_unitario) 
                VALUES ($1, $2, $3, $4);
            """, compra_id, item.producto_id, item.cantidad, item.costo_unitario)
            
            await conn.execute("""
                UPDATE producto 
                SET stock = stock + $1, costo = $2 
                WHERE id = $3;
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


