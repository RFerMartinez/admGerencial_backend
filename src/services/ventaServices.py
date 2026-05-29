# src/services/ventaServices.py
import asyncpg
from asyncpg import Connection
from schemas.ventaSchema import VentaCreate
from utils.exceptions import BadRequestException, NotFoundException, DatabaseException

async def procesar_venta(conn: Connection, venta_data: VentaCreate) -> dict:
    # Bloque Transaccional ACID: O se guarda todo, o se revierte automáticamente
    async with conn.transaction():
        
        # --- PREPARACIÓN Y VALIDACIÓN ---
        costo_total_venta = 0.0
        
        # 1. Validar stock y calcular Costo Total (CMV) consultando la tabla producto
        for item in venta_data.items:
            # Traemos stock, nombre y costo. Bloqueamos la fila con FOR UPDATE.
            prod = await conn.fetchrow("""
                SELECT nombre, stock, costo 
                FROM producto 
                WHERE id = $1 FOR UPDATE;
            """, item.producto_id)
            
            if not prod:
                raise NotFoundException(detail=f"El producto con ID {item.producto_id} no existe.")
            
            if prod['stock'] < item.cantidad:
                raise BadRequestException(detail=f"Stock insuficiente para '{prod['nombre']}'. Disponible: {prod['stock']}.")
            
            # Calculamos el costo multiplicando la cantidad por el costo unitario de la base de datos
            costo_unitario = float(prod['costo'])
            costo_total_venta += costo_unitario * item.cantidad

        # 2. Mapeo de Cuentas (Buscar IDs dinámicamente por código)
        codigo_cobro = '1.1.1.01' if venta_data.metodo_pago.lower() == 'efectivo' else '1.1.1.02'
        
        cuentas_necesarias = [codigo_cobro, '4.1.01', '5.1.01', '1.1.5.01']
        cuentas_ids = {}
        for cod in cuentas_necesarias:
            cuenta = await conn.fetchrow("SELECT id FROM cuentas WHERE codigo = $1;", cod)
            if not cuenta:
                raise DatabaseException(detail=f"Falla de configuración contable: No se encontró la cuenta {cod}.")
            cuentas_ids[cod] = cuenta['id']

        # --- PASO 1: ASIENTO CONTABLE (Cabecera) ---
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        descripcion_asiento = f"Venta Mostrador - {venta_data.metodo_pago}"
        asiento_id = await conn.fetchval(query_asiento, venta_data.fecha.date(), descripcion_asiento)

        # --- PASO 2: REGISTRO OPERATIVO (Venta Cabecera) ---
        query_venta = "INSERT INTO ventas (fecha, total, asiento_id) VALUES ($1, $2, $3) RETURNING id;"
        venta_id = await conn.fetchval(query_venta, venta_data.fecha.date(), venta_data.total, asiento_id)

        # --- PASO 3: DETALLES DE VENTA Y DESCUENTO DE STOCK ---
        for item in venta_data.items:
            # Insertar renglón de venta
            await conn.execute("""
                INSERT INTO ventas_detalle (venta_id, producto_id, cantidad, precio_unitario) 
                VALUES ($1, $2, $3, $4);
            """, venta_id, item.producto_id, item.cantidad, item.precio_unitario)
            
            # Actualizar stock
            await conn.execute("""
                UPDATE producto SET stock = stock - $1 WHERE id = $2;
            """, item.cantidad, item.producto_id)

        # --- PASO 4: PARTIDA DOBLE (Asientos Detalle) ---
        renglones_contables = [
            # 1. Ingreso de Dinero (Caja o Banco) -> Activo Sube (Debe)
            (asiento_id, cuentas_ids[codigo_cobro], venta_data.total, 0.00),
            # 2. Ganancia por Venta -> Ingreso Sube (Haber)
            (asiento_id, cuentas_ids['4.1.01'], 0.00, venta_data.total),
            # 3. Costo de Mercadería Vendida (CMV) -> Egreso Sube (Debe)
            (asiento_id, cuentas_ids['5.1.01'], costo_total_venta, 0.00),
            # 4. Salida de Mercadería -> Activo Baja (Haber)
            (asiento_id, cuentas_ids['1.1.5.01'], 0.00, costo_total_venta)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) 
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        # Retornamos el resultado
        return {
            "id": venta_id,
            "fecha": venta_data.fecha.date(),
            "total": venta_data.total,
            "asiento_id": asiento_id
        }

