from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.services.auth_service import login_user
from app.schemas.auth import LoginRequest, LoginResponse
from app.models.persona import Persona
from app.schemas.auth import RegisterRequest
from app.services.auth_service import register_user

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post("/login", response_model=LoginResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db)
):
    return login_user(
        db=db,
        email=data.email,
        password=data.password
    )

@router.get("/me", status_code=status.HTTP_200_OK)
def obtener_usuario_actual(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    persona = (
        db.query(Persona)
        .filter(Persona.auth_user_id == auth_user_id)
        .first()
    )

    if not persona:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no autorizado."
        )

    return {
        "id_persona": persona.id_persona,
        "nombre": persona.nombre,
        "apellido": persona.apellido,
        "rol": persona.rol,
        "perfil": persona.perfil
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    auth_user_id: str = Depends(get_current_user_id)
):
    return {"success": True}

@router.post("/register")
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db)
):
    return register_user(
        db=db,
        nombre=data.nombre,
        apellido=data.apellido,
        email=data.email,
        password=data.password,
        foto_url=data.foto_url
    )
