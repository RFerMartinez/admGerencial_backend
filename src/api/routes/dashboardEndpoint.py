from fastapi import APIRouter, Depends, status
from core.session import get_db
from services import dashboardServices

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/", status_code=status.HTTP_200_OK)
async def obtener_dashboard(conn=Depends(get_db)):
    return await dashboardServices.obtener_dashboard(conn)
