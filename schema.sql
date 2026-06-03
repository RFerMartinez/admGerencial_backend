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