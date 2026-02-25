from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.persona import Persona
from app.models.person_role import PersonRole
from app.models.estado import Estado
from app.schemas.estado import EstadoUpdate, EstadoResponse

router = APIRouter(prefix="/config", tags=["Config"])


def _verificar_pastor(auth_user_id: str, db: Session):
    persona = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    roles = [pr.id_rol for pr in db.query(PersonRole).filter(PersonRole.person_id == persona.id_persona).all()]
    if 1 not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los pastores pueden modificar la configuración de estados"
        )


@router.put("/estados", response_model=list[EstadoResponse])
def actualizar_estados(
    estados: list[EstadoUpdate],
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Actualiza la lista de estados disponibles.
    Solo accesible por pastores (rol=1).
    Acepta una lista de objetos con id_estado y los campos a modificar (nombre, orden, activo).
    """
    _verificar_pastor(auth_user_id, db)

    actualizados = []
    for item in estados:
        estado = db.query(Estado).filter(Estado.id_estado == item.id_estado).first()
        if not estado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Estado con id_estado={item.id_estado} no encontrado"
            )
        if item.nombre is not None:
            estado.nombre = item.nombre
        if item.orden is not None:
            estado.orden = item.orden
        if item.activo is not None:
            estado.activo = item.activo
        actualizados.append(estado)

    db.commit()
    for e in actualizados:
        db.refresh(e)

    return actualizados
