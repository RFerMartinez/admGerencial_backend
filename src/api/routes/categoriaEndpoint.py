from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from schemas.categoriaSchema import CategoriaCreate, CategoriaUpdate, CategoriaResponse
from services import categoriaServices

router = APIRouter(prefix="/categorias", tags=["Categorías"])

@router.get("/", response_model=List[CategoriaResponse], status_code=status.HTTP_200_OK)
async def listar_categorias(conn: Connection = Depends(get_db)):
    """Obtiene la lista de todas las categorías disponibles."""
    return await categoriaServices.get_all_categorias(conn)

@router.get("/{nombre}", response_model=CategoriaResponse, status_code=status.HTTP_200_OK)
async def obtener_categoria(nombre: str, conn: Connection = Depends(get_db)):
    """Obtiene una categoría específica buscando por su nombre exacto."""
    return await categoriaServices.get_categoria_by_nombre(conn, nombre)

@router.post("/", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED)
async def crear_categoria(categoria: CategoriaCreate, conn: Connection = Depends(get_db)):
    """Crea una nueva categoría."""
    return await categoriaServices.create_categoria(conn, categoria)

@router.put("/{nombre_actual}", response_model=CategoriaResponse, status_code=status.HTTP_200_OK)
async def actualizar_categoria(nombre_actual: str, categoria: CategoriaUpdate, conn: Connection = Depends(get_db)):
    """
    Actualiza el nombre de una categoría. 
    Nota: Gracias al constraint ON UPDATE CASCADE de PostgreSQL, los productos 
    asociados a esta categoría se actualizarán automáticamente a este nuevo nombre.
    """
    return await categoriaServices.update_categoria(conn, nombre_actual, categoria)

@router.delete("/{nombre}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_categoria(nombre: str, conn: Connection = Depends(get_db)):
    """
    Elimina una categoría.
    Fallará (Status 400) si existen productos actualmente asociados a esta categoría.
    """
    await categoriaServices.delete_categoria(conn, nombre)
    return

