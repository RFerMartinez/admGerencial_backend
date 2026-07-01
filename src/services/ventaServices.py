# src/services/ventaServices.py
import random
from asyncpg import Connection
from schemas.ventaSchema import VentaCreate
from utils.exceptions import BadRequestException, NotFoundException, DatabaseException
from services.clienteServices import obtener_o_crear_silencioso
from services.cuentaSistemaServices import resolver_cuentas_sistema
from services.cierreServices import validar_periodo_abierto
from datetime import datetime

async def procesar_venta(conn: Connection, venta_data: VentaCreate) -> dict:
    # Bloque Transaccional ACID
    async with conn.transaction():

        await validar_periodo_abierto(conn, venta_data.fecha)

        # --- PREPARACIÓN Y VALIDACIÓN ---
        costo_total_venta = 0.0
        
        # 1. Validar stock y calcular Costo Total (CMV) consultando la tabla producto
        for item in venta_data.items:
            prod = await conn.fetchrow("""
                SELECT nombre, stock, costo 
                FROM producto 
                WHERE id = $1 FOR UPDATE;
            """, item.producto_id)
            
            if not prod:
                raise NotFoundException(detail=f"El producto con ID {item.producto_id} no existe.")
            
            if prod['stock'] < item.cantidad:
                raise BadRequestException(detail=f"Stock insuficiente para '{prod['nombre']}'. Disponible: {prod['stock']}.")
            
            costo_unitario = float(prod['costo'])
            costo_total_venta += costo_unitario * item.cantidad

        # 2. ENRUTAMIENTO CONTABLE DINÁMICO
        if venta_data.metodo_pago == "Efectivo":
            rol_cobro = 'CAJA'
        elif venta_data.metodo_pago == "Transferencia":
            rol_cobro = 'BANCO'
        else:
            raise BadRequestException(detail="Método de pago no soportado por el sistema.")

        config = await resolver_cuentas_sistema(conn, [rol_cobro, 'VENTAS', 'CMV', 'MERCADERIAS'])

        # --- PASO 1: ASIENTO CONTABLE (Cabecera) ---
        # Se combina la fecha ingresada por el usuario con la hora actual del servidor,
        # para no depender de datetime.now() para la fecha (evita el corrimiento de día
        # por zona horaria) pero conservando un orden cronológico dentro del mismo día.
        query_asiento = "INSERT INTO asientos (fecha, descripcion) VALUES ($1, $2) RETURNING id;"
        descripcion_asiento = f"Venta s/ {venta_data.tipo_comprobante} - {venta_data.metodo_pago.capitalize()}"
        fecha_asiento = datetime.combine(venta_data.fecha, datetime.now().time())
        asiento_id = await conn.fetchval(query_asiento, fecha_asiento, descripcion_asiento)

        # --- PASO 2: REGISTRO OPERATIVO Y DOCUMENTAL ---
        
        # A. Lógica Inteligente de Cliente y Upsert Silencioso
        cuit_final = '00000000000'
        cliente_nom = 'Consumidor Final'
        cliente_iva = 'Consumidor Final'
        cliente_domicilio = ''

        # Si NO es Factura B y enviaron datos de cliente, usamos esos datos
        if venta_data.tipo_comprobante != "Factura B" and venta_data.cliente:
            cuit_final = venta_data.cliente.cuit or venta_data.cliente.identificacion or cuit_final
            cliente_nom = venta_data.cliente.razon_social or cliente_nom
            cliente_iva = venta_data.cliente.condicion_iva or cliente_iva
            cliente_domicilio = venta_data.cliente.domicilio or cliente_domicilio

        # Aseguramos que el cliente exista en la nueva tabla (Upsert)
        await obtener_o_crear_silencioso(
            conn, 
            cuit=cuit_final, 
            razon_social=cliente_nom, 
            domicilio=cliente_domicilio, 
            condicion_iva=cliente_iva
        )

        # B. Extracción segura de desglose de impuestos
        subtotal = iva = None
        if venta_data.impuestos:
            subtotal = venta_data.impuestos.subtotal_neto
            iva = venta_data.impuestos.iva_21

        # C. Generador de Nro de Comprobante
        nro_comprobante = "S/N"
        if venta_data.tipo_comprobante != "Ticket":
            nro_comprobante = f"0001-{random.randint(10000, 99999)}"

        # D. Inserción en la base de datos operativa (tabla ventas)
        query_venta = """
            INSERT INTO ventas (fecha, total, asiento_id) 
            VALUES ($1, $2, $3) RETURNING id;
        """
        venta_id = await conn.fetchval(
            query_venta, 
            venta_data.fecha, 
            venta_data.total, 
            asiento_id
        )

        # E. Inserción en la base de datos documental (tabla documentos_contables)
        query_documento = """
            INSERT INTO documentos_contables (
                tipo_comprobante, nro_comprobante, fecha_emision, total,
                cliente_proveedor_nombre, cliente_proveedor_identificacion, condicion_iva,
                subtotal_neto, iva_21, venta_id, cliente_cuit
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            ) RETURNING id;
        """
        await conn.fetchval(
            query_documento,
            venta_data.tipo_comprobante,
            nro_comprobante,
            venta_data.fecha,
            venta_data.total,
            cliente_nom,
            cuit_final,  # Usamos cuit_final también en cliente_proveedor_identificacion para retrocompatibilidad
            cliente_iva,
            subtotal,
            iva,
            venta_id,
            cuit_final   # $11: Foreign Key a la tabla clientes
        )

        # --- PASO 3: DETALLES DE VENTA Y DESCUENTO DE STOCK ---
        for item in venta_data.items:
            await conn.execute("""
                INSERT INTO ventas_detalle (venta_id, producto_id, cantidad, precio_unitario) 
                VALUES ($1, $2, $3, $4);
            """, venta_id, item.producto_id, item.cantidad, item.precio_unitario)
            
            await conn.execute("""
                UPDATE producto SET stock = stock - $1 WHERE id = $2;
            """, item.cantidad, item.producto_id)

        # --- PASO 4: PARTIDA DOBLE ---
        renglones_contables = [
            (asiento_id, config[rol_cobro], venta_data.total, 0.00),
            (asiento_id, config['VENTAS'], 0.00, venta_data.total),
            (asiento_id, config['CMV'], costo_total_venta, 0.00),
            (asiento_id, config['MERCADERIAS'], 0.00, costo_total_venta)
        ]

        await conn.executemany("""
            INSERT INTO asientos_detalle (asiento_id, cuenta_id, debe, haber) 
            VALUES ($1, $2, $3, $4);
        """, renglones_contables)

        return {
            "id": venta_id,
            "fecha": venta_data.fecha,
            "total": venta_data.total,
            "asiento_id": asiento_id,
            "tipo_comprobante": venta_data.tipo_comprobante,
            "nro_comprobante": nro_comprobante
        }