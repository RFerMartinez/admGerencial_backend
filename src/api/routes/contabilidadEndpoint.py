# src/api/routes/contabilidadEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection
from typing import List

from core.session import get_db
from schemas.contabilidadSchema import AsientoDiario
from services import contabilidadServices

router = APIRouter(prefix="/contabilidad", tags=["Reportes Contables"])

@router.get(
    "/libro-diario", 
    response_model=List[AsientoDiario], 
    status_code=status.HTTP_200_OK
)
async def consultar_libro_diario(conn: Connection = Depends(get_db)):
    """
    Obtiene todos los asientos contables registrados y sus detalles.
    
    Devuelve la información estructurada y agrupada por asiento, 
    calculando automáticamente el cuadre (total Debe y total Haber) 
    para su renderización en el frontend.
    """
    return await contabilidadServices.obtener_libro_diario(conn)

