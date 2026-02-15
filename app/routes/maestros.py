from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.maestro import Maestro
from app.models.persona import Persona
from app.schemas.auth import RegisterMaestroRequest
from app.services.auth_service import register_maestro
from app.schemas.auth import MaestroUpdate, ChangeProfileRequest
from app.models.person_role import PersonRole
from app.core.security import hash_password
from app.models.role import Role
from app.models.profile import Profile

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
            "email": persona.email if persona else None,
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
        "email": persona.email if persona else None,
        "telefono": maestro.telefono,
        "direccion": maestro.direccion,
        "created_at": maestro.created_at.isoformat() if getattr(maestro, "created_at", None) else None
    }


@router.post("", status_code=201)
def create_maestro(
    data: RegisterMaestroRequest,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo maestro (persona + maestro + rol) usando la lógica de `register_maestro`.
    Requiere autenticación.
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


@router.put("/{id_maestro}")
def update_maestro(
    id_maestro: str,
    data: MaestroUpdate,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Actualiza datos de un maestro y su persona asociada.
    - Pastores (rol=1) pueden actualizar cualquiera.
    - Maestros (rol=2) solo pueden actualizar su propio registro.
    """

    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    # roles
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    es_pastor = 1 in roles
    es_maestro = 2 in roles

    if not es_pastor and not es_maestro:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para actualizar maestros")

    maestro = db.query(Maestro).filter(Maestro.id_maestro == id_maestro).first()
    if not maestro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maestro con id {id_maestro} no encontrado")

    # si es maestro, verificar que sea el suyo
    if es_maestro and not es_pastor:
        maestro_propio = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro_propio or str(maestro_propio.id_maestro) != str(id_maestro):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No puedes actualizar este maestro")

    persona = db.query(Persona).filter(Persona.id_persona == maestro.id_persona).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona asociada no encontrada")

    update_data = data.model_dump(exclude_unset=True)

    # actualizar persona
    if "nombre" in update_data:
        persona.nombre = update_data["nombre"]
    if "apellido" in update_data:
        persona.apellido = update_data["apellido"]
    if "email" in update_data:
        persona.email = update_data["email"]
    if "foto_url" in update_data:
        persona.foto_url = update_data["foto_url"]
    if "password" in update_data and update_data["password"]:
        persona.password = hash_password(update_data["password"])

    # actualizar maestro
    if "telefono" in update_data:
        maestro.telefono = update_data["telefono"]
    if "direccion" in update_data:
        maestro.direccion = update_data["direccion"]

    try:
        db.commit()
        db.refresh(maestro)
        db.refresh(persona)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al actualizar maestro: {str(e)}")

    return {
        "id_maestro": str(maestro.id_maestro),
        "id_persona": str(maestro.id_persona),
        "nombre": persona.nombre,
        "apellido": persona.apellido,
        "email": persona.email,
        "telefono": maestro.telefono,
        "direccion": maestro.direccion,
        "created_at": maestro.created_at.isoformat() if getattr(maestro, "created_at", None) else None
    }


@router.patch("/{id_maestro}/permisos")
def change_maestro_permissions(
    id_maestro: str,
    data: ChangeProfileRequest,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Cambia el perfil de un maestro (ej: de Usuario a Administrador).
    Solo accesible por pastores (rol=1).
    Los perfiles disponibles son: Administrador, Moderador, Usuario.
    """
    
    # Verificar que el usuario autenticado sea un pastor
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # Verificar que el usuario autenticado es pastor
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    es_pastor = 1 in roles
    
    if not es_pastor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los pastores pueden cambiar permisos"
        )
    
    # Verificar que el maestro existe
    maestro = db.query(Maestro).filter(Maestro.id_maestro == id_maestro).first()
    if not maestro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maestro con id {id_maestro} no encontrado"
        )
    
    # Verificar que el perfil a asignar existe
    perfil_nuevo = db.query(Profile).filter(Profile.id_perfil == data.id_perfil).first()
    if not perfil_nuevo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Perfil con id {data.id_perfil} no encontrado"
        )
    
    # Obtener la persona asociada al maestro
    persona = db.query(Persona).filter(Persona.id_persona == maestro.id_persona).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona asociada al maestro no encontrada"
        )
    
    # Verificar si ya tiene ese perfil
    if persona.id_perfil == data.id_perfil:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El maestro ya tiene el perfil '{perfil_nuevo.descripcion}'"
        )
    
    # Guardar el perfil anterior para el mensaje
    perfil_anterior = db.query(Profile).filter(Profile.id_perfil == persona.id_perfil).first()
    
    # Cambiar el perfil del maestro
    try:
        persona.id_perfil = data.id_perfil
        db.commit()
        db.refresh(persona)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar perfil: {str(e)}"
        )
    
    # Obtener roles del maestro
    all_roles = db.query(PersonRole).filter(PersonRole.person_id == maestro.id_persona).all()
    roles_list = []
    for pr in all_roles:
        role = db.query(Role).filter(Role.id_rol == pr.id_rol).first()
        if role:
            roles_list.append({
                "id_rol": role.id_rol,
                "descripcion": role.descripcion
            })
    
    return {
        "message": f"Perfil cambiado de '{perfil_anterior.descripcion if perfil_anterior else 'Desconocido'}' a '{perfil_nuevo.descripcion}' exitosamente",
        "id_maestro": str(maestro.id_maestro),
        "id_persona": str(maestro.id_persona),
        "nombre": persona.nombre,
        "apellido": persona.apellido,
        "perfil_actual": {
            "id_perfil": perfil_nuevo.id_perfil,
            "descripcion": perfil_nuevo.descripcion,
            "nivel_acceso": perfil_nuevo.nivel_acceso
        },
        "roles": roles_list
    }


@router.delete("/{id_maestro}")
def delete_maestro(
    id_maestro: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Elimina un maestro y la persona asociada. Solo permitido para pastores (rol=1).
    """

    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    es_pastor = 1 in roles

    if not es_pastor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para eliminar maestros")

    maestro = db.query(Maestro).filter(Maestro.id_maestro == id_maestro).first()
    if not maestro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Maestro con id {id_maestro} no encontrado")

    persona = db.query(Persona).filter(Persona.id_persona == maestro.id_persona).first()

    try:
        # Borrar la persona (las FK con ON DELETE CASCADE limpiarán maestro, person_roles, etc.)
        if persona:
            db.delete(persona)
        else:
            db.delete(maestro)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error al eliminar maestro: {str(e)}")

    return {"message": "Maestro eliminado correctamente", "id_maestro": str(id_maestro)}
