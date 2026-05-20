from fastapi.responses import JSONResponse
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.config import settings
from core.session import connect_to_db, close_db_connection

from utils.exceptions import APIException

from api.routes import productoEndpoint

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

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message
        }
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productoEndpoint.router, prefix="/api/v1")

if __name__ == "__main__":
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True
    )