# src/api/routes/contabilidadEndpoint.py
from fastapi import APIRouter, Depends, Query, status
from asyncpg import Connection
from typing import List, Optional

from core.session import get_db
from schemas.contabilidadSchema import AsientoDiario, CuentaLibroMayor, AsientoManualCreate
from services import contabilidadServices

router = APIRouter(prefix="/contabilidad", tags=["Reportes Contables"])


@router.get("/libro-diario", response_model=List[AsientoDiario], status_code=status.HTTP_200_OK)
async def consultar_libro_diario(
    periodo: Optional[str] = Query(None, description="Filtrar por período YYYY-MM"),
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    conn: Connection = Depends(get_db)
):
    return await contabilidadServices.obtener_libro_diario(conn, periodo=periodo, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


@router.get("/libro-mayor", response_model=List[CuentaLibroMayor], status_code=status.HTTP_200_OK)
async def consultar_libro_mayor(
    periodo: Optional[str] = Query(None, description="Filtrar por período YYYY-MM"),
    fecha_desde: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    fecha_hasta: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    conn: Connection = Depends(get_db)
):
    return await contabilidadServices.obtener_libro_mayor(conn, periodo=periodo, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta)


@router.get("/balance", status_code=status.HTTP_200_OK)
async def consultar_balance(
    fecha: Optional[str] = Query(None, description="Balance acumulado hasta esta fecha YYYY-MM-DD (default: hoy)"),
    conn: Connection = Depends(get_db)
):
    return await contabilidadServices.obtener_balance(conn, fecha=fecha)


@router.post("/asientos-manuales", status_code=status.HTTP_201_CREATED)
async def registrar_asiento_manual(asiento_data: AsientoManualCreate, conn: Connection = Depends(get_db)):
    return await contabilidadServices.registrar_asiento_manual(conn, asiento_data)
