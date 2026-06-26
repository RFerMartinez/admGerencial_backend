from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.session import connect_to_db, close_db_connection


from api.routes import (
    productoEndpoint,
    categoriaEndpoint,
    cuentaEndpoint,
    ventaEndpoint,
    compraEndpoint,
    contabilidadEndpoint,
    proveedorEndpoint,
    capitalEndpoint,
    documentoEndpoint,
    clienteEndpoint,
    cuentaSistemaEndpoint,
    gastoEndpoint,
    proveedorMaestroEndpoint,
    cierreEndpoint
    )

# Lifespan para administrar la conexión asíncrona de base de datos
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Conectando al pool de la base de datos (SQL Crudo)...")
    await connect_to_db()
    yield
    print("Cerrando el pool de conexiones...")
    await close_db_connection()

# Inicialización
app = FastAPI(
    title=settings.PROJECT_TITLE,
    description=settings.PROJECT_DESCRIPTION,
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productoEndpoint.router)
app.include_router(categoriaEndpoint.router)
app.include_router(cuentaEndpoint.router)
app.include_router(ventaEndpoint.router)
app.include_router(compraEndpoint.router)
app.include_router(contabilidadEndpoint.router)
app.include_router(proveedorEndpoint.router)
app.include_router(capitalEndpoint.router)
app.include_router(documentoEndpoint.router)
app.include_router(clienteEndpoint.router, prefix="/clientes", tags=["Clientes"])
app.include_router(cuentaSistemaEndpoint.router)
app.include_router(gastoEndpoint.router)
app.include_router(proveedorMaestroEndpoint.router)
app.include_router(cierreEndpoint.router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )