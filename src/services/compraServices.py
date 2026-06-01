# src/services/compraServices.py
import asyncpg
from asyncpg import Connection
from schemas.compraSchema import CompraCreate
from utils.exceptions import NotFoundException, DatabaseException

async def procesar_compra(conn: Connection, compra_data: CompraCreate) -> dict:
    # Transacción ACID: O se completa todo, o se deshace todo automáticamente
    async with conn.transaction():
        
        # --- PREPARACIÓN Y VALIDACIÓN ---
        
        # 1. Validar que los productos enviados existan (Bloqueamos fila para evitar colisiones)
        for item in compra_data.detalles:
            prod = await conn.fetchrow("""
                SELECT id FROM producto WHERE id = $1 FOR UPDATE;
            """, item.producto_id)
            
            if not prod:
                raise NotFoundException(detail=f"El producto con ID {item.producto_id} no existe.")

        # 2. Mapeo de Cuentas Contables (Buscar IDs por código)
        codigo_pago = '1.1.1.01' if compra_data.metodo_pago.lower() == 'efectivo' else '1.1.1.02'
        codigo_mercaderias = '1.1.5.01'
        
        cuentas_ids = {}
        for cod in [codigo_pago, codigo_mercaderias]:
            cuenta = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", cod)
            if not cuenta:
                raise DatabaseException(detail=f"Falla contable: No se encontró la cuenta con código {cod}.")
            cuentas_ids[cod] = cuenta['id']

        # --- PASO 1: ASIENTO CONTABLE (Cabecera) ---
        descripcion_asiento = f"Compra s/ {compra_data.tipo_comprobante} {compra_data.nro_comprobante}"
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        asiento_id = await conn.fetchval(query_asiento, compra_data.fecha, descripcion_asiento)

        # --- PASO 2: REGISTRO OPERATIVO (Compra Cabecera) ---
        query_compra = """
            INSERT INTO compras_mercaderia (fecha, total, asiento_id, tipo_comprobante, nro_comprobante) 
            VALUES ($1, $2, $3, $4, $5) RETURNING id;
        """
        compra_id = await conn.fetchval(
            query_compra, 
            compra_data.fecha, 
            compra_data.total, 
            asiento_id, 
            compra_data.tipo_comprobante, 
            compra_data.nro_comprobante
        )

        # --- PASO 3: DETALLES DE COMPRA Y ACTUALIZACIÓN (INVENTARIO/COSTO) ---
        for item in compra_data.detalles:
            # A) Guardar renglón de compra
            await conn.execute("""
                INSERT INTO compras_detalle (compra_id, producto_id, cantidad, costo_unitario) 
                VALUES ($1, $2, $3, $4);
            """, compra_id, item.producto_id, item.cantidad, item.costo_unitario)
            
            # B) Actualizar Stock e ingresar el nuevo Costo Unitario
            await conn.execute("""
                UPDATE producto 
                SET stock = stock + $1, costo = $2 
                WHERE id = $3;
            """, item.cantidad, item.costo_unitario, item.producto_id)

        # --- PASO 4: PARTIDA DOBLE (Renglones Contables) ---
        renglones_contables = [
            # 1. Ingreso de Activo al Inventario -> Mercaderías Sube (Debe)
            (asiento_id, cuentas_ids[codigo_mercaderias], compra_data.total, 0.00),
            # 2. Salida de Dinero -> Caja o Banco Baja (Haber)
            (asiento_id, cuentas_ids[codigo_pago], 0.00, compra_data.total)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) 
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        return {
            "id": compra_id,
            "fecha": compra_data.fecha,
            "total": compra_data.total,
            "asiento_id": asiento_id
        }

