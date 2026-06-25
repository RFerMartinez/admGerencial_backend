-- DROP SCHEMA public;

CREATE SCHEMA public AUTHORIZATION pg_database_owner;

-- DROP SEQUENCE public.asientos_detalle_id_seq;

CREATE SEQUENCE public.asientos_detalle_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.asientos_id_seq;

CREATE SEQUENCE public.asientos_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.compras_detalle_id_seq;

CREATE SEQUENCE public.compras_detalle_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.compras_mercaderia_id_seq;

CREATE SEQUENCE public.compras_mercaderia_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.cuentas_id_seq;

CREATE SEQUENCE public.cuentas_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.producto_id_seq;

CREATE SEQUENCE public.producto_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.ventas_detalle_id_seq;

CREATE SEQUENCE public.ventas_detalle_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;
-- DROP SEQUENCE public.ventas_id_seq;

CREATE SEQUENCE public.ventas_id_seq
	INCREMENT BY 1
	MINVALUE 1
	MAXVALUE 2147483647
	START 1
	CACHE 1
	NO CYCLE;-- public.asientos definition

-- Drop table

-- DROP TABLE public.asientos;

CREATE TABLE public.asientos (
	id serial4 NOT NULL,
	fecha date NOT NULL,
	descripcion varchar(255) NOT NULL,
	CONSTRAINT asientos_pkey PRIMARY KEY (id)
);


-- public.categorias definition

-- Drop table

-- DROP TABLE public.categorias;

CREATE TABLE public.categorias (
	nombre varchar(50) NOT NULL,
	CONSTRAINT categorias_pkey PRIMARY KEY (nombre)
);


-- public.cuentas definition

-- Drop table

-- DROP TABLE public.cuentas;

CREATE TABLE public.cuentas (
	id serial4 NOT NULL,
	nombre varchar(100) NOT NULL,
	tipo varchar(20) NOT NULL,
	codigo varchar(20) NULL,
	CONSTRAINT cuentas_pkey PRIMARY KEY (id),
	CONSTRAINT cuentas_tipo_check CHECK (((tipo)::text = ANY (ARRAY[('Activo'::character varying)::text, ('Pasivo'::character varying)::text, ('Patrimonio Neto'::character varying)::text, ('Ingreso'::character varying)::text, ('Egreso'::character varying)::text])))
);


-- public.asientos_detalle definition

-- Drop table

-- DROP TABLE public.asientos_detalle;

CREATE TABLE public.asientos_detalle (
	id serial4 NOT NULL,
	asiento_id int4 NOT NULL,
	cuenta_id int4 NOT NULL,
	debe numeric(12, 2) DEFAULT 0.00 NULL,
	haber numeric(12, 2) DEFAULT 0.00 NULL,
	CONSTRAINT asientos_detalle_pkey PRIMARY KEY (id),
	CONSTRAINT asientos_detalle_asiento_id_fkey FOREIGN KEY (asiento_id) REFERENCES public.asientos(id) ON DELETE CASCADE,
	CONSTRAINT asientos_detalle_cuenta_id_fkey FOREIGN KEY (cuenta_id) REFERENCES public.cuentas(id)
);


-- public.compras_mercaderia definition

-- Drop table

-- DROP TABLE public.compras_mercaderia;

CREATE TABLE public.compras_mercaderia (
	id serial4 NOT NULL,
	fecha date NOT NULL,
	total numeric(12, 2) NOT NULL,
	asiento_id int4 NOT NULL,
	tipo_comprobante varchar(50) DEFAULT 'Ticket'::character varying NOT NULL,
	nro_comprobante varchar(50) DEFAULT 'S/N'::character varying NOT NULL,
	CONSTRAINT compras_mercaderia_pkey PRIMARY KEY (id),
	CONSTRAINT compras_mercaderia_asiento_id_fkey FOREIGN KEY (asiento_id) REFERENCES public.asientos(id)
);


-- public.producto definition

-- Drop table

-- DROP TABLE public.producto;

CREATE TABLE public.producto (
	id serial4 NOT NULL,
	nombre varchar(150) NOT NULL,
	precio numeric(10, 2) NOT NULL,
	stock int4 DEFAULT 0 NOT NULL,
	tipo varchar(50) NOT NULL,
	costo numeric(10, 2) DEFAULT 0.00 NOT NULL,
	CONSTRAINT producto_pkey PRIMARY KEY (id),
	CONSTRAINT producto_precio_check CHECK ((precio >= (0)::numeric)),
	CONSTRAINT producto_stock_check CHECK ((stock >= 0)),
	CONSTRAINT fk_producto_categoria FOREIGN KEY (tipo) REFERENCES public.categorias(nombre) ON UPDATE CASCADE,
	CONSTRAINT fk_producto_tipo FOREIGN KEY (tipo) REFERENCES public.categorias(nombre) ON UPDATE CASCADE
);


-- public.ventas definition

-- Drop table

-- DROP TABLE public.ventas;

CREATE TABLE public.ventas (
	id serial4 NOT NULL,
	fecha date NOT NULL,
	total numeric(12, 2) NOT NULL,
	asiento_id int4 NOT NULL,
	CONSTRAINT ventas_pkey PRIMARY KEY (id),
	CONSTRAINT ventas_asiento_id_fkey FOREIGN KEY (asiento_id) REFERENCES public.asientos(id)
);


-- public.ventas_detalle definition

-- Drop table

-- DROP TABLE public.ventas_detalle;

CREATE TABLE public.ventas_detalle (
	id serial4 NOT NULL,
	venta_id int4 NOT NULL,
	producto_id int4 NOT NULL,
	cantidad int4 NOT NULL,
	precio_unitario numeric(12, 2) NOT NULL,
	CONSTRAINT ventas_detalle_pkey PRIMARY KEY (id),
	CONSTRAINT ventas_detalle_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.producto(id),
	CONSTRAINT ventas_detalle_venta_id_fkey FOREIGN KEY (venta_id) REFERENCES public.ventas(id) ON DELETE CASCADE
);


-- public.compras_detalle definition

-- Drop table

-- DROP TABLE public.compras_detalle;

CREATE TABLE public.compras_detalle (
	id serial4 NOT NULL,
	compra_id int4 NOT NULL,
	producto_id int4 NOT NULL,
	cantidad int4 NOT NULL,
	costo_unitario numeric(12, 2) NOT NULL,
	CONSTRAINT compras_detalle_pkey PRIMARY KEY (id),
	CONSTRAINT compras_detalle_compra_id_fkey FOREIGN KEY (compra_id) REFERENCES public.compras_mercaderia(id) ON DELETE CASCADE,
	CONSTRAINT compras_detalle_producto_id_fkey FOREIGN KEY (producto_id) REFERENCES public.producto(id)
);


-- public.clientes definition

CREATE TABLE public.clientes (
	cuit varchar(20) NOT NULL,
	razon_social varchar(255) NULL,
	domicilio_fiscal varchar(255) NULL,
	condicion_iva varchar(50) NULL,
	CONSTRAINT clientes_pkey PRIMARY KEY (cuit)
);


-- public.documentos_contables definition

CREATE TABLE public.documentos_contables (
	id serial4 NOT NULL,
	tipo_comprobante varchar(50) NOT NULL,
	nro_comprobante varchar(50) NOT NULL,
	fecha_emision date NOT NULL,
	total numeric(12, 2) NOT NULL,
	cliente_proveedor_nombre varchar(150) NULL,
	cliente_proveedor_identificacion varchar(50) NULL,
	condicion_iva varchar(50) NULL,
	subtotal_neto numeric(12, 2) NULL,
	iva_21 numeric(12, 2) NULL,
	venta_id int4 NULL,
	compra_id int4 NULL,
	comprobante_padre_id int4 NULL,
	tipo_operacion varchar(50) NULL,
	entidad_nombre varchar(150) NULL,
	cliente_cuit varchar(20) NULL,
	gasto_id int4 NULL,
	CONSTRAINT documentos_contables_pkey PRIMARY KEY (id),
	CONSTRAINT documentos_contables_cliente_cuit_fkey FOREIGN KEY (cliente_cuit) REFERENCES public.clientes(cuit),
	CONSTRAINT fk_dc_compra FOREIGN KEY (compra_id) REFERENCES public.compras_mercaderia(id) ON DELETE CASCADE,
	CONSTRAINT fk_dc_padre FOREIGN KEY (comprobante_padre_id) REFERENCES public.documentos_contables(id),
	CONSTRAINT fk_dc_venta FOREIGN KEY (venta_id) REFERENCES public.ventas(id) ON DELETE CASCADE
);


-- public.cuentas_sistema definition

CREATE TABLE public.cuentas_sistema (
	rol varchar(50) NOT NULL,
	cuenta_id int4 NOT NULL,
	CONSTRAINT cuentas_sistema_pkey PRIMARY KEY (rol),
	CONSTRAINT cuentas_sistema_cuenta_id_fkey FOREIGN KEY (cuenta_id) REFERENCES public.cuentas(id)
);


-- public.gastos definition

CREATE TABLE public.gastos (
	id serial4 NOT NULL,
	fecha date NOT NULL,
	descripcion varchar(255) NOT NULL,
	cuenta_debe_id int4 NOT NULL,
	monto numeric(12, 2) NOT NULL,
	asiento_id int4 NOT NULL,
	CONSTRAINT gastos_pkey PRIMARY KEY (id),
	CONSTRAINT gastos_cuenta_fkey FOREIGN KEY (cuenta_debe_id) REFERENCES public.cuentas(id),
	CONSTRAINT gastos_asiento_fkey FOREIGN KEY (asiento_id) REFERENCES public.asientos(id)
);

ALTER TABLE public.documentos_contables ADD CONSTRAINT fk_dc_gasto
	FOREIGN KEY (gasto_id) REFERENCES public.gastos(id) ON DELETE CASCADE;


-- Seed: cuentas_sistema (ejecutar después de tener las cuentas cargadas)
-- INSERT INTO cuentas_sistema (rol, cuenta_id)
-- SELECT 'CAJA', id FROM cuentas WHERE codigo = '110001' UNION ALL
-- SELECT 'BANCO', id FROM cuentas WHERE codigo = '110003' UNION ALL
-- SELECT 'MERCADERIAS', id FROM cuentas WHERE codigo = '140002' UNION ALL
-- SELECT 'VENTAS', id FROM cuentas WHERE codigo = '410001' UNION ALL
-- SELECT 'CMV', id FROM cuentas WHERE codigo = '510007' UNION ALL
-- SELECT 'CAPITAL', id FROM cuentas WHERE codigo = '300001';