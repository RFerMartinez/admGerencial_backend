# src/api/routes/productoEndpoint.py
from fastapi import APIRouter, Depends
from asyncpg import Connection
from typing import Any

from core.session import get_db
from schemas.productoSchema import ProductoCreate, ProductoUpdate
from services import productoServices

router = APIRouter(prefix="/productos", tags=["Productos"])

@router.get("/", response_model=dict[str, Any])
async def listar_productos(conn: Connection = Depends(get_db)):
    data = await productoServices.get_all_productos(conn)
    return {"status": "success", "data": data}

@router.get("/{producto_id}", response_model=dict[str, Any])
async def obtener_producto(producto_id: int, conn: Connection = Depends(get_db)):
    data = await productoServices.get_producto_by_id(conn, producto_id)
    return {"status": "success", "data": data}

@router.post("/", response_model=dict[str, Any], status_code=201)
async def crear_producto(producto: ProductoCreate, conn: Connection = Depends(get_db)):
    data = await productoServices.create_producto(conn, producto)
    return {"status": "success", "data": data}

@router.put("/{producto_id}", response_model=dict[str, Any])
async def actualizar_producto(producto_id: int, producto: ProductoUpdate, conn: Connection = Depends(get_db)):
    data = await productoServices.update_producto(conn, producto_id, producto)
    return {"status": "success", "data": data}

@router.delete("/{producto_id}", response_model=dict[str, Any])
async def eliminar_producto(producto_id: int, conn: Connection = Depends(get_db)):
    await productoServices.delete_producto(conn, producto_id)
    return {"status": "success", "message": f"Producto {producto_id} eliminado exitosamente."}

