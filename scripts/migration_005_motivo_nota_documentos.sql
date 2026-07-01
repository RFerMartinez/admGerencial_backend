-- Migración 005: guardar el motivo de una Nota de Crédito/Débito directamente
-- en documentos_contables, en vez de reconstruirlo comparando fechas contra
-- la tabla asientos (comparación timestamp = date que en la práctica nunca
-- coincidía, porque el asiento siempre tiene una hora distinta de medianoche).
-- Ejecutar manualmente contra la base de datos existente.

ALTER TABLE public.documentos_contables ADD COLUMN motivo_nota varchar(255) NULL;
