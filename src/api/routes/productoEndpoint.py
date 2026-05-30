# src/api/routes/productoEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from schemas.productoSchema import ProductoCreate, ProductoUpdate, ProductoResponse
from services import productoServices

router = APIRouter(prefix="/productos", tags=["Productos"])

@router.get("/", response_model=List[ProductoResponse], status_code=status.HTTP_200_OK)
async def listar_productos(conn: Connection = Depends(get_db)):
    """Obtiene la lista completa de productos incluyendo el costo."""
    # Retornamos los datos crudos directamente (el array)
    return await productoServices.get_all_productos(conn)

@router.get("/{producto_id}", response_model=ProductoResponse, status_code=status.HTTP_200_OK)
async def obtener_producto(producto_id: int, conn: Connection = Depends(get_db)):
    """Obtiene un producto específico por su ID."""
    return await productoServices.get_producto_by_id(conn, producto_id)

@router.post("/", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED)
async def crear_producto(producto: ProductoCreate, conn: Connection = Depends(get_db)):
    """Crea un nuevo producto en el sistema definiendo precio, costo y categoría."""
    return await productoServices.create_producto(conn, producto)

@router.put("/{producto_id}", response_model=ProductoResponse, status_code=status.HTTP_200_OK)
async def actualizar_producto(producto_id: int, producto: ProductoUpdate, conn: Connection = Depends(get_db)):
    """Actualiza de manera parcial los atributos de un producto."""
    return await productoServices.update_producto(conn, producto_id, producto)

@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_producto(producto_id: int, conn: Connection = Depends(get_db)):
    """Elimina un producto siempre y cuando no registre movimientos previos."""
    await productoServices.delete_producto(conn, producto_id)
    return

