from fastapi import APIRouter, Depends, status
from typing import List
from core.session import get_db
from schemas.proveedorMaestroSchema import ProveedorCreate, ProveedorResponse, ProveedorEstadoUpdate
from services import proveedorMaestroServices

router = APIRouter(prefix="/proveedores/maestro", tags=["Proveedores - Maestro"])


@router.get("/", response_model=List[ProveedorResponse], status_code=status.HTTP_200_OK)
async def listar_proveedores(incluir_inactivos: bool = False, conn=Depends(get_db)):
    return await proveedorMaestroServices.obtener_todos(conn, solo_activos=not incluir_inactivos)


@router.get("/{proveedor_id}", response_model=ProveedorResponse, status_code=status.HTTP_200_OK)
async def obtener_proveedor(proveedor_id: int, conn=Depends(get_db)):
    return await proveedorMaestroServices.obtener_por_id(conn, proveedor_id)


@router.post("/", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED)
async def crear_proveedor(data: ProveedorCreate, conn=Depends(get_db)):
    return await proveedorMaestroServices.crear(conn, data)


@router.put("/{proveedor_id}", response_model=ProveedorResponse, status_code=status.HTTP_200_OK)
async def actualizar_proveedor(proveedor_id: int, data: ProveedorCreate, conn=Depends(get_db)):
    return await proveedorMaestroServices.actualizar(conn, proveedor_id, data)


@router.patch("/{proveedor_id}/estado", response_model=ProveedorResponse, status_code=status.HTTP_200_OK)
async def cambiar_estado_proveedor(proveedor_id: int, data: ProveedorEstadoUpdate, conn=Depends(get_db)):
    return await proveedorMaestroServices.cambiar_estado(conn, proveedor_id, data.activo)
