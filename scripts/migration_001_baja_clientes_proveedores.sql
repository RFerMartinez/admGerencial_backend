-- Migración 001: baja lógica de clientes y proveedores
-- Ejecutar manualmente contra la base de datos existente.

ALTER TABLE public.clientes ADD COLUMN activo boolean NOT NULL DEFAULT true;
ALTER TABLE public.proveedores ADD COLUMN activo boolean NOT NULL DEFAULT true;
