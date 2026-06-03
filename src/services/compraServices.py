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

        # --- ENRUTAMIENTO CONTABLE (HABER) ---
        cuenta_haber_id = None
        
        if compra_data.tipo_comprobante == "Cuenta Corriente":
            # USAMOS DIRECTAMENTE EL ID DEL FRONTEND
            cuenta_haber_id = compra_data.cuenta_proveedor_id
            
            # Verificamos por seguridad que el ID enviado realmente exista en la tabla cuentas
            cuenta_existe = await conn.fetchval("SELECT id FROM cuentas WHERE id = $1;", cuenta_haber_id)
            if not cuenta_existe:
                raise NotFoundException(detail=f"La cuenta contable con ID {cuenta_haber_id} no existe en el plan de cuentas.")
        else:
            # Si es factura pagada al contado, buscamos el ID de la caja o banco por su código
            if compra_data.metodo_pago == "Efectivo":
                codigo_haber = '110001' # Caja
            elif compra_data.metodo_pago in ["Transferencia", "Tarjeta"]:
                codigo_haber = '110003' # Banco
                
            cuenta = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", codigo_haber)
            if not cuenta:
                raise DatabaseException(detail=f"Falla contable: No se encontró la cuenta con código {codigo_haber}.")
            cuenta_haber_id = cuenta['id']

        # --- ENRUTAMIENTO CONTABLE (DEBE) ---
        # Cuenta Mercaderías (Siempre entra la mercadería)
        cuenta_mercaderias = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = '140002';")
        if not cuenta_mercaderias:
            raise DatabaseException(detail="Falla contable: No se encontró la cuenta de Mercaderías (140002).")
        cuenta_debe_id = cuenta_mercaderias['id']

        # --- PASO 1: ASIENTO CONTABLE (Cabecera) ---
        if compra_data.tipo_comprobante == "Cuenta Corriente":
            descripcion_asiento = "Compra en Cuenta Corriente"
        else:
            descripcion_asiento = f"Compra s/ {compra_data.tipo_comprobante} {compra_data.nro_comprobante}"
            
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        asiento_id = await conn.fetchval(query_asiento, compra_data.fecha, descripcion_asiento)

        # --- PASO 2: REGISTRO OPERATIVO ---
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
            (asiento_id, cuenta_debe_id, compra_data.total, 0.00),  # Debe (Mercaderías)
            (asiento_id, cuenta_haber_id, 0.00, compra_data.total)  # Haber (El ID que mandó el front, o Caja/Banco)
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

