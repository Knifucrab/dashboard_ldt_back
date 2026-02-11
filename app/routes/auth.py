from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.services.auth_service import login_user, register_user, register_maestro, register_alumno
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, RegisterMaestroRequest, RegisterAlumnoRequest
from app.models.persona import Persona

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
        "rol": persona.id_rol,
        "perfil": persona.id_perfil
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
        foto_url=data.foto_url,
        id_rol=data.id_rol,
        id_perfil=data.id_perfil
    )

@router.post("/register/maestro")
def register_maestro_endpoint(
    data: RegisterMaestroRequest,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo maestro.
    Crea automáticamente registros en 'personas' y 'maestros'.
    """
    return register_maestro(
        db=db,
        nombre=data.nombre,
        apellido=data.apellido,
        email=data.email,
        password=data.password,
        foto_url=data.foto_url,
        telefono=data.telefono,
        direccion=data.direccion
    )

@router.post("/register/alumno")
def register_alumno_endpoint(
    data: RegisterAlumnoRequest,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo alumno.
    Crea automáticamente registros en 'personas', 'alumnos' y 'tarjetas'.
    El alumno queda asignado al maestro especificado.
    """
    return register_alumno(
        db=db,
        nombre=data.nombre,
        apellido=data.apellido,
        maestro_asignado=data.maestro_asignado,
        foto_url=data.foto_url,
        dias=data.dias,
        franja_horaria=data.franja_horaria,
        motivo_oracion=data.motivo_oracion
    )
