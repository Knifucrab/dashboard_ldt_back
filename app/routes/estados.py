from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.estado import EstadoCreate, EstadoResponse
from app.services.estado_service import crear_estado
from app.dependencies import get_db
from app.models.estado import Estado 

router = APIRouter(prefix="/estados", tags=["Estados"])


@router.post("/", response_model=EstadoResponse)
def crear_estado_endpoint(
    data: EstadoCreate,
    db: Session = Depends(get_db)
):
    try:
        estado = crear_estado(
            db=db,
            nombre=data.nombre,
            orden=data.orden
        )
        return estado
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=list[EstadoResponse])
def listar_estados(db: Session = Depends(get_db)):
    estados = (
        db.query(Estado)
        .order_by(Estado.orden)
        .all()
    )
    return estados
