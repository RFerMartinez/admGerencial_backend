from fastapi import APIRouter, Depends, status
from typing import List
from core.session import get_db
from schemas.cierreSchema import CierreCreate, CierreResponse, CierrePreview, CierreListItem
from services import cierreServices

router = APIRouter(prefix="/cierres", tags=["Cierres Contables"])


@router.get("/", status_code=status.HTTP_200_OK)
async def listar_cierres(conn=Depends(get_db)):
    return await cierreServices.obtener_historial(conn)


@router.get("/preview/{periodo}", status_code=status.HTTP_200_OK)
async def preview_cierre(periodo: str, conn=Depends(get_db)):
    return await cierreServices.preview_cierre(conn, periodo)


@router.get("/{cierre_id}", status_code=status.HTTP_200_OK)
async def detalle_cierre(cierre_id: int, conn=Depends(get_db)):
    return await cierreServices.obtener_cierre_detalle(conn, cierre_id)


@router.post("/", response_model=CierreResponse, status_code=status.HTTP_201_CREATED)
async def ejecutar_cierre(data: CierreCreate, conn=Depends(get_db)):
    return await cierreServices.ejecutar_cierre(conn, data)
