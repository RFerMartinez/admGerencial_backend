-- Migración 002: registrar el método de pago real de cada compra/gasto
-- Necesario para distinguir "proveedor solo de seguimiento" (pago al contado)
-- de "proveedor con deuda real" (Cuenta Corriente) en el cálculo de deudas.
-- Ejecutar manualmente contra la base de datos existente.

ALTER TABLE public.compras_mercaderia ADD COLUMN metodo_pago varchar(20) NULL;
ALTER TABLE public.gastos ADD COLUMN metodo_pago varchar(20) NULL;

-- Backfill de registros históricos: las compras/gastos que ya tenían proveedor_id
-- cargado (antes de este cambio) siempre fueron a Cuenta Corriente, porque era
-- la única forma de asociar un proveedor. Las que no tienen proveedor fueron al contado.
UPDATE public.compras_mercaderia SET metodo_pago = 'Cuenta Corriente' WHERE proveedor_id IS NOT NULL AND metodo_pago IS NULL;
UPDATE public.compras_mercaderia SET metodo_pago = 'Efectivo' WHERE proveedor_id IS NULL AND metodo_pago IS NULL;

UPDATE public.gastos SET metodo_pago = 'Cuenta Corriente' WHERE proveedor_id IS NOT NULL AND metodo_pago IS NULL;
UPDATE public.gastos SET metodo_pago = 'Efectivo' WHERE proveedor_id IS NULL AND metodo_pago IS NULL;

