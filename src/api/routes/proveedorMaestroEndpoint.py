from fastapi import APIRouter, Depends, status
from typing import List
from core.session import get_db
from schemas.proveedorMaestroSchema import ProveedorCreate, ProveedorResponse
from services import proveedorMaestroServices

router = APIRouter(prefix="/proveedores/maestro", tags=["Proveedores - Maestro"])


@router.get("/", response_model=List[ProveedorResponse], status_code=status.HTTP_200_OK)
async def listar_proveedores(conn=Depends(get_db)):
    return await proveedorMaestroServices.obtener_todos(conn)


@router.get("/{proveedor_id}", response_model=ProveedorResponse, status_code=status.HTTP_200_OK)
async def obtener_proveedor(proveedor_id: int, conn=Depends(get_db)):
    return await proveedorMaestroServices.obtener_por_id(conn, proveedor_id)


@router.post("/", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED)
async def crear_proveedor(data: ProveedorCreate, conn=Depends(get_db)):
    return await proveedorMaestroServices.crear(conn, data)


@router.put("/{proveedor_id}", response_model=ProveedorResponse, status_code=status.HTTP_200_OK)
async def actualizar_proveedor(proveedor_id: int, data: ProveedorCreate, conn=Depends(get_db)):
    return await proveedorMaestroServices.actualizar(conn, proveedor_id, data)


@router.delete("/{proveedor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_proveedor(proveedor_id: int, conn=Depends(get_db)):
    await proveedorMaestroServices.eliminar(conn, proveedor_id)
