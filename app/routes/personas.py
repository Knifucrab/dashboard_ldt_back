from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.persona import Persona
from app.models.person_role import PersonRole
from app.models.role import Role
from app.models.profile import Profile
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.tarjeta import Tarjeta
from app.schemas.auth import PersonaUpdate
from app.core.security import hash_password

router = APIRouter(prefix="/personas", tags=["Personas"])


@router.get("")
def get_personas(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Devuelve la lista de todas las personas registradas en el sistema.
    
    Requiere autenticación. Solo accesible por pastores (rol=1).
    Retorna información de la persona, su perfil y roles asignados.
    """

    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    es_administrador = persona_autenticada.id_perfil == 1
    es_moderador = persona_autenticada.id_perfil == 2

    if not es_administrador and not es_moderador:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para ver personas"
        )

    # --- Administrador (id_perfil=1): devuelve todas las personas ---
    if es_administrador:
        personas = db.query(Persona).all()

    # --- Moderador (id_perfil=2): devuelve sus alumnos + pastores + sí mismo ---
    else:
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró el registro de maestro para este usuario"
            )

        # IDs de personas de sus alumnos asignados
        tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == maestro.id_maestro).all()
        id_alumnos = [t.id_alumno for t in tarjetas]
        alumnos = db.query(Alumno).filter(Alumno.id_alumno.in_(id_alumnos)).all()
        id_personas_alumnos = {a.id_persona for a in alumnos}

        # IDs de personas con rol=1 (pastor)
        roles_pastor = db.query(PersonRole).filter(PersonRole.id_rol == 1).all()
        id_personas_pastores = {pr.person_id for pr in roles_pastor}

        # Unión: alumnos + pastores + sí mismo
        ids_visibles = id_personas_alumnos | id_personas_pastores | {persona_autenticada.id_persona}

        personas = db.query(Persona).filter(Persona.id_persona.in_(ids_visibles)).all()

    result = []
    for persona in personas:
        perfil = db.query(Profile).filter(Profile.id_perfil == persona.id_perfil).first()

        person_roles_list = db.query(PersonRole).filter(PersonRole.person_id == persona.id_persona).all()
        roles_list = []
        for pr in person_roles_list:
            role = db.query(Role).filter(Role.id_rol == pr.id_rol).first()
            if role:
                roles_list.append({
                    "id_rol": role.id_rol,
                    "descripcion": role.descripcion
                })

        persona_data = {
            "id_persona": str(persona.id_persona),
            "auth_user_id": str(persona.auth_user_id),
            "nombre": persona.nombre,
            "apellido": persona.apellido,
            "email": persona.email,
            "foto_url": persona.foto_url,
            "perfil": {
                "id_perfil": perfil.id_perfil,
                "descripcion": perfil.descripcion,
                "nivel_acceso": perfil.nivel_acceso
            } if perfil else None,
            "roles": roles_list,
            "created_at": persona.created_at.isoformat() if persona.created_at else None
        }

        # Verificar si es maestro y agregar información de maestro
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona.id_persona).first()
        if maestro:
            persona_data["maestro_info"] = {
                "id_maestro": str(maestro.id_maestro),
                "telefono": maestro.telefono,
                "direccion": maestro.direccion,
                "created_at": maestro.created_at.isoformat() if maestro.created_at else None
            }

        # Verificar si es alumno y agregar información de alumno
        alumno = db.query(Alumno).filter(Alumno.id_persona == persona.id_persona).first()
        if alumno:
            # Buscar el maestro asignado a través de la tabla tarjetas
            tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == alumno.id_alumno).first()
            
            maestro_asignado = None
            if tarjeta and tarjeta.id_maestro_asignado:
                maestro_rel = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro_asignado).first()
                if maestro_rel:
                    persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_rel.id_persona).first()
                    if persona_maestro:
                        maestro_asignado = {
                            "id_maestro": str(maestro_rel.id_maestro),
                            "id_persona": str(persona_maestro.id_persona),
                            "nombre": persona_maestro.nombre,
                            "apellido": persona_maestro.apellido,
                            "email": persona_maestro.email
                        }
            
            persona_data["alumno_info"] = {
                "id_alumno": str(alumno.id_alumno),
                "dias": alumno.dias,
                "franja_horaria": alumno.franja_horaria,
                "motivo_oracion": alumno.motivo_oracion,
                "id_estado_actual": alumno.id_estado_actual,
                "maestro_asignado": maestro_asignado,
                "created_at": alumno.created_at.isoformat() if alumno.created_at else None
            }

        result.append(persona_data)

    return {
        "personas": result,
        "total": len(result)
    }


@router.get("/{id_persona}")
def get_persona_by_id(
    id_persona: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Devuelve una persona por su ID con detalles completos según su rol.
    
    Requiere autenticación. Solo accesible por pastores (rol=1).
    
    Si la persona es maestro: incluye datos de maestro (teléfono, dirección)
    Si la persona es alumno: incluye datos de alumno (días, franja horaria, motivo de oración, maestro asignado)
    """

    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # Verificar que sea pastor
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    es_pastor = 1 in roles

    if not es_pastor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los pastores pueden ver los detalles de las personas"
        )

    # Buscar la persona
    persona = db.query(Persona).filter(Persona.id_persona == id_persona).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona con id {id_persona} no encontrada"
        )

    # Obtener perfil
    perfil = db.query(Profile).filter(Profile.id_perfil == persona.id_perfil).first()
    
    # Obtener roles
    person_roles_list = db.query(PersonRole).filter(PersonRole.person_id == persona.id_persona).all()
    roles_list = []
    for pr in person_roles_list:
        role = db.query(Role).filter(Role.id_rol == pr.id_rol).first()
        if role:
            roles_list.append({
                "id_rol": role.id_rol,
                "descripcion": role.descripcion
            })
    
    # Datos base de la persona
    result = {
        "id_persona": str(persona.id_persona),
        "auth_user_id": str(persona.auth_user_id),
        "nombre": persona.nombre,
        "apellido": persona.apellido,
        "email": persona.email,
        "foto_url": persona.foto_url,
        "perfil": {
            "id_perfil": perfil.id_perfil,
            "descripcion": perfil.descripcion,
            "nivel_acceso": perfil.nivel_acceso
        } if perfil else None,
        "roles": roles_list,
        "created_at": persona.created_at.isoformat() if persona.created_at else None
    }
    
    # Verificar si es maestro
    maestro = db.query(Maestro).filter(Maestro.id_persona == persona.id_persona).first()
    if maestro:
        result["maestro_info"] = {
            "id_maestro": str(maestro.id_maestro),
            "telefono": maestro.telefono,
            "direccion": maestro.direccion,
            "created_at": maestro.created_at.isoformat() if maestro.created_at else None
        }
    
    # Verificar si es alumno
    alumno = db.query(Alumno).filter(Alumno.id_persona == persona.id_persona).first()
    if alumno:
        # Buscar el maestro asignado a través de la tabla tarjetas
        from app.models.tarjeta import Tarjeta
        tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == alumno.id_alumno).first()
        
        maestro_asignado = None
        if tarjeta:
            maestro_rel = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro).first()
            if maestro_rel:
                persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_rel.id_persona).first()
                if persona_maestro:
                    maestro_asignado = {
                        "id_maestro": str(maestro_rel.id_maestro),
                        "id_persona": str(persona_maestro.id_persona),
                        "nombre": persona_maestro.nombre,
                        "apellido": persona_maestro.apellido,
                        "email": persona_maestro.email
                    }
        
        result["alumno_info"] = {
            "id_alumno": str(alumno.id_alumno),
            "dias": alumno.dias,
            "franja_horaria": alumno.franja_horaria,
            "motivo_oracion": alumno.motivo_oracion,
            "id_estado_actual": alumno.id_estado_actual,
            "maestro_asignado": maestro_asignado,
            "created_at": alumno.created_at.isoformat() if alumno.created_at else None
        }
    
    return result


@router.put("/{id_persona}")
def update_persona(
    id_persona: str,
    data: PersonaUpdate,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Actualiza la información general de una persona.
    
    Requiere autenticación. Solo accesible por pastores (rol=1).
    Permite actualizar: nombre, apellido, email, foto_url y password.
    """

    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # Verificar que sea pastor
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    es_pastor = 1 in roles

    if not es_pastor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los pastores pueden actualizar personas"
        )

    # Buscar la persona a actualizar
    persona = db.query(Persona).filter(Persona.id_persona == id_persona).first()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Persona con id {id_persona} no encontrada"
        )

    # Obtener datos a actualizar
    update_data = data.model_dump(exclude_unset=True)

    # Verificar si el email ya está en uso por otra persona
    if "email" in update_data and update_data["email"] != persona.email:
        email_existente = db.query(Persona).filter(
            Persona.email == update_data["email"],
            Persona.id_persona != id_persona
        ).first()
        if email_existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está en uso por otra persona"
            )

    # Actualizar campos
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

    try:
        db.commit()
        db.refresh(persona)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar persona: {str(e)}"
        )

    # Obtener perfil actualizado
    perfil = db.query(Profile).filter(Profile.id_perfil == persona.id_perfil).first()
    
    # Obtener roles
    person_roles_list = db.query(PersonRole).filter(PersonRole.person_id == persona.id_persona).all()
    roles_list = []
    for pr in person_roles_list:
        role = db.query(Role).filter(Role.id_rol == pr.id_rol).first()
        if role:
            roles_list.append({
                "id_rol": role.id_rol,
                "descripcion": role.descripcion
            })

    return {
        "message": "Persona actualizada exitosamente",
        "id_persona": str(persona.id_persona),
        "auth_user_id": str(persona.auth_user_id),
        "nombre": persona.nombre,
        "apellido": persona.apellido,
        "email": persona.email,
        "foto_url": persona.foto_url,
        "perfil": {
            "id_perfil": perfil.id_perfil,
            "descripcion": perfil.descripcion,
            "nivel_acceso": perfil.nivel_acceso
        } if perfil else None,
        "roles": roles_list,
        "created_at": persona.created_at.isoformat() if persona.created_at else None
    }
