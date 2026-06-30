-- Migración 004: vincular documentos_contables con su pago_proveedor de origen
-- Permite mostrar el detalle completo (proveedor, método de pago, observaciones, asiento)
-- al desplegar un documento de tipo 'Pago' en la sección Documentos.
-- Ejecutar manualmente contra la base de datos existente.

ALTER TABLE public.documentos_contables ADD COLUMN pago_id int4 NULL;
ALTER TABLE public.documentos_contables ADD CONSTRAINT fk_dc_pago
	FOREIGN KEY (pago_id) REFERENCES public.pagos_proveedor(id) ON DELETE CASCADE;

-- Nota: los pagos históricos (registrados antes de esta migración) quedarán con
-- pago_id = NULL porque no hay forma confiable de re-vincularlos retroactivamente.
-- Solo los pagos nuevos, registrados después de actualizar el backend, tendrán
-- el detalle completo de trazabilidad.
