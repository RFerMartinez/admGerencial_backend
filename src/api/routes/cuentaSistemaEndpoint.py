from fastapi import APIRouter, Depends, status
from core.session import get_db
from schemas.cuentaSistemaSchema import CuentaSistemaUpdate
from services import cuentaSistemaServices

router = APIRouter(prefix="/config/cuentas-sistema", tags=["Configuración"])


@router.get("/", status_code=status.HTTP_200_OK)
async def listar_configuracion(conn=Depends(get_db)):
    return await cuentaSistemaServices.obtener_configuracion(conn)


@router.put("/{rol}", status_code=status.HTTP_200_OK)
async def actualizar_configuracion(rol: str, body: CuentaSistemaUpdate, conn=Depends(get_db)):
    return await cuentaSistemaServices.actualizar_rol(conn, rol, body.cuenta_id)
