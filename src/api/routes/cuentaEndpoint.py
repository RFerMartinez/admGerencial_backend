# src/api/routes/cuentaEndpoint.py
from fastapi import APIRouter, Depends, status
from asyncpg import Connection

from core.session import get_db
from schemas.cuentaSchema import CuentaCreate, CuentaUpdate, CuentaResponse, CuentaListResponse
from services import cuentaServices

router = APIRouter(
    prefix="/cuentas",
    tags=["Plan de Cuentas"]
    )

@router.get("/",
            response_model=CuentaListResponse,
            status_code=status.HTTP_200_OK
            )
async def listar_cuentas(
    conn: Connection = Depends(get_db)
    ):
    """Obtiene el plan de cuentas completo ordenado jerárquicamente por su código."""
    cuentas = await cuentaServices.get_all_cuentas(conn)
    return {
        "status": "success",
        "data": cuentas
    }

@router.get("/{cuenta_id}",
            response_model=CuentaResponse,
            status_code=status.HTTP_200_OK
            )
async def obtener_cuenta(
    cuenta_id: int,
    conn: Connection = Depends(get_db)
    ):
    """Obtiene la información detallada de una cuenta contable específica."""
    return await cuentaServices.get_cuenta_by_id(conn, cuenta_id)

@router.post("/",
            response_model=CuentaResponse,
            status_code=status.HTTP_201_CREATED
            )
async def crear_cuenta(
    cuenta: CuentaCreate,
    conn: Connection = Depends(get_db)
    ):
    """Registra una nueva cuenta en el plan de cuentas."""
    return await cuentaServices.create_cuenta(conn, cuenta)

@router.put("/{cuenta_id}",
            response_model=CuentaResponse, 
            status_code=status.HTTP_200_OK
            )
async def actualizar_cuenta(
    cuenta_id: int,
    cuenta: CuentaUpdate,
    conn: Connection = Depends(get_db)
    ):
    """Actualiza de forma parcial los atributos de una cuenta contable existente."""
    return await cuentaServices.update_cuenta(conn, cuenta_id, cuenta)

@router.delete("/{cuenta_id}",
            status_code=status.HTTP_204_NO_CONTENT
            )
async def eliminar_cuenta(
    cuenta_id: int,
    conn: Connection = Depends(get_db)
    ):
    """
    Remueve una cuenta contable del catálogo.
    Dará error 400 si la cuenta ya posee registros vinculados en la contabilidad.
    """
    await cuentaServices.delete_cuenta(conn, cuenta_id)
    return

