-- Migración 003: teléfono de contacto para clientes
-- Ejecutar manualmente contra la base de datos existente.

ALTER TABLE public.clientes ADD COLUMN telefono varchar(50) NULL;
