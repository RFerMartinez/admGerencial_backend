# Sistema de Gestión y Contabilidad (API)

Este proyecto es una API RESTful desarrollada con **FastAPI** para la materia **Administración Gerencial**. El software está diseñado para simular la administración de un comercio minorista (como un kiosco), automatizando la relación entre el flujo de mercadería y las obligaciones contables.

## 🚀 Características Principales

* **Control de Stock:** Registro de productos, actualización de inventario y manejo de existencias.
* **Módulo de Facturación:** Carga de facturas de compra y venta.
* **Módulo Contable:** Generación automática de los 3 tipos de libros contables principales a partir de los movimientos de facturación y stock.

## 🏗️ Arquitectura y Estructura

El proyecto utiliza una arquitectura modular en capas para separar responsabilidades, facilitar la escalabilidad y mantener el código ordenado:

* `src/api/routes`: Endpoints expuestos de la API.
* `src/services`: Lógica de negocio, cálculos contables y transacciones de base de datos.
* `src/schemas`: Modelos de Pydantic para la validación estricta de datos de entrada y salida.
* `src/core`: Configuraciones centrales (variables de entorno, conexión a BD).
* `src/utils`: Herramientas auxiliares y manejo de excepciones.

## 🛠️ Tecnologías Utilizadas

* **Framework:** FastAPI
* **Lenguaje:** Python 3.x
* **Validación:** Pydantic
* **Base de Datos:** PostgreSQL *(adaptar si usas otra)*

## ⚙️ Instalación y Configuración Local

1. **Clonar el repositorio:**
   ```bash
   git clone <URL_DE_TU_REPOSITORIO>
   cd kiosko_contable_api
   ```

2. **Crear y activar el entorno virtual:**
   * En Windows:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * En Linux / macOS:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. **Instalar las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar el entorno:**
   Crear un archivo `.env` en el directorio raíz asegurando configurar las credenciales de la base de datos local y puertos correspondientes.

## ▶️ Ejecución

Para iniciar el servidor local de desarrollo, ejecuta:

```bash
uvicorn src.main:app --reload
```

Una vez que el servidor esté corriendo, puedes explorar y probar todos los endpoints a través de la documentación interactiva (Swagger UI) ingresando a:
`http://127.0.0.1:8000/docs`