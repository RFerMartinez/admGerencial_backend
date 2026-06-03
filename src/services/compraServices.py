# src/services/compraServices.py
import asyncpg
from asyncpg import Connection
from schemas.compraSchema import CompraCreate
from utils.exceptions import NotFoundException, DatabaseException

async def procesar_compra(conn: Connection, compra_data: CompraCreate) -> dict:
    async with conn.transaction():
        
        # --- PREPARACIÓN Y VALIDACIÓN DE PRODUCTOS ---
        for item in compra_data.detalles:
            prod = await conn.fetchrow("""
                SELECT id FROM producto WHERE id = $1 FOR UPDATE;
            """, item.producto_id)
            
            if not prod:
                raise NotFoundException(detail=f"El producto con ID {item.producto_id} no existe.")

        # --- ENRUTAMIENTO CONTABLE INTELIGENTE ---
        codigo_haber = None
        
        if compra_data.tipo_comprobante == "Cuenta Corriente":
            codigo_haber = '210001' # Proveedores
        else:
            if compra_data.metodo_pago == "Efectivo":
                codigo_haber = '110001' # Caja
            elif compra_data.metodo_pago in ["Transferencia", "Tarjeta"]:
                codigo_haber = '110003' # Banco Nación Cta.Cte.

        codigo_mercaderias = '140002' # Cuenta del Debe (Siempre entra la mercadería)
        
        # Buscar IDs internos de las cuentas
        cuentas_ids = {}
        for cod in [codigo_haber, codigo_mercaderias]:
            cuenta = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", cod)
            if not cuenta:
                raise DatabaseException(detail=f"Falla contable: No se encontró la cuenta con código {cod}.")
            cuentas_ids[cod] = cuenta['id']

        # --- PASO 1: ASIENTO CONTABLE (Cabecera) ---
        if compra_data.tipo_comprobante == "Cuenta Corriente":
            descripcion_asiento = "Compra en Cuenta Corriente"
        else:
            descripcion_asiento = f"Compra s/ {compra_data.tipo_comprobante} {compra_data.nro_comprobante}"
            
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        asiento_id = await conn.fetchval(query_asiento, compra_data.fecha, descripcion_asiento)

        # --- PASO 2: REGISTRO OPERATIVO ---
        # Recordatorio: Si decides agregar cuenta_proveedor_id a tu tabla compras_mercaderia, 
        # debes añadir el campo en este INSERT.
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
            (asiento_id, cuentas_ids[codigo_mercaderias], compra_data.total, 0.00), # Debe (Ingreso al stock)
            (asiento_id, cuentas_ids[codigo_haber], 0.00, compra_data.total)      # Haber (Deuda o Salida de caja)
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

