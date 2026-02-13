from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.maestro import Maestro
from app.models.persona import Persona

router = APIRouter(prefix="/maestros", tags=["Maestros"])


@router.get("")
def get_maestros(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Devuelve la lista de maestros.

    Requiere autenticación. Retorna datos básicos de la persona y del maestro.
    """

    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    maestros = db.query(Maestro).all()
    result = []
    for m in maestros:
        persona = db.query(Persona).filter(Persona.id_persona == m.id_persona).first()
        result.append({
            "id_maestro": str(m.id_maestro),
            "id_persona": str(m.id_persona),
            "nombre": persona.nombre if persona else None,
            "apellido": persona.apellido if persona else None,
            "telefono": m.telefono,
            "direccion": m.direccion,
            "created_at": m.created_at.isoformat() if getattr(m, "created_at", None) else None
        })

    return {"maestros": result, "total": len(result)}


@router.get("/{id_maestro}")
def get_maestro_by_id(
    id_maestro: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Devuelve un maestro por su `id_maestro`.

    Requiere autenticación. Valida existencia y devuelve datos de persona + maestro.
    """

    # Verificar usuario autenticado
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    maestro = db.query(Maestro).filter(Maestro.id_maestro == id_maestro).first()
    if not maestro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maestro con id {id_maestro} no encontrado")

    persona = db.query(Persona).filter(Persona.id_persona == maestro.id_persona).first()

    return {
        "id_maestro": str(maestro.id_maestro),
        "id_persona": str(maestro.id_persona),
        "nombre": persona.nombre if persona else None,
        "apellido": persona.apellido if persona else None,
        "telefono": maestro.telefono,
        "direccion": maestro.direccion,
        "created_at": maestro.created_at.isoformat() if getattr(maestro, "created_at", None) else None
    }
