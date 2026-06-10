# src/api/routes/capitalEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection

from core.session import get_db
from schemas.capitalSchema import CapitalInicialCreate, CapitalResponse
from services import capitalServices

router = APIRouter(prefix="/capital", tags=["Configuración Inicial"])

@router.post("/", response_model=CapitalResponse, status_code=status.HTTP_201_CREATED)
async def registrar_capital(capital_data: CapitalInicialCreate, conn: Connection = Depends(get_db)):
    """
    Registra el asiento contable de apertura (Capital Inicial).
    
    Toma los saldos iniciales de caja y banco, los ingresa al activo, 
    y reconoce el patrimonio neto en la cuenta de Capital Social (300001).
    Todo bajo una única transacción atómica SQL.
    """
    return await capitalServices.registrar_capital_inicial(conn, capital_data)

