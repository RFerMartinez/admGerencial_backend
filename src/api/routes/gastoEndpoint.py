from fastapi import APIRouter, Depends, status
from core.session import get_db
from schemas.gastoSchema import GastoCreate, GastoResponse
from services import gastoServices

router = APIRouter(prefix="/gastos", tags=["Gastos"])


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=GastoResponse)
async def registrar_gasto(gasto: GastoCreate, conn=Depends(get_db)):
    return await gastoServices.registrar_gasto(conn, gasto)


@router.get("/", status_code=status.HTTP_200_OK)
async def listar_gastos(conn=Depends(get_db)):
    return await gastoServices.obtener_gastos(conn)
