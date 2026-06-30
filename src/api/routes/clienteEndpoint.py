from fastapi import APIRouter, Depends, HTTPException, status
from asyncpg import Connection
# Reemplaza 'get_db' por el nombre exacto que uses en tus otros endpoints
from core.session import get_db
from schemas.clienteSchema import ClienteCreate, ClienteResponse, ClienteEstadoUpdate, ClienteBase
from services import clienteServices

router = APIRouter()

@router.get("/", response_model=list[ClienteResponse])
async def listar_clientes(incluir_inactivos: bool = False, conn: Connection = Depends(get_db)): # <-- Usar la misma función aquí
    try:
        return await clienteServices.obtener_todos(conn, solo_activos=not incluir_inactivos)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
async def registrar_nuevo_cliente(cliente: ClienteCreate, conn: Connection = Depends(get_db)): # <-- Y aquí
    try:
        return await clienteServices.crear_cliente(conn, cliente)
    except Exception as e:
         raise HTTPException(status_code=400, detail="Error al crear el cliente, posible CUIT duplicado.")

@router.patch("/{cuit}/estado", response_model=ClienteResponse)
async def cambiar_estado_cliente(cuit: str, data: ClienteEstadoUpdate, conn: Connection = Depends(get_db)):
    return await clienteServices.cambiar_estado(conn, cuit, data.activo)

@router.put("/{cuit}", response_model=ClienteResponse)
async def actualizar_cliente(cuit: str, data: ClienteBase, conn: Connection = Depends(get_db)):
    return await clienteServices.actualizar_cliente(conn, cuit, data)
