from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.persona import Persona
from app.models.person_role import PersonRole
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.tarjeta import Tarjeta
from app.schemas.alumno import AlumnoUpdate

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])

@router.get("")
def get_alumnos(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    maestroId: Optional[str] = Query(None, description="ID de persona del maestro para filtrar alumnos (solo para pastores)")
):
    """
    Obtiene alumnos según el rol del usuario autenticado.
    
    - Si role === 'pastor' (id_rol=1):
      * Sin maestroId: devuelve TODOS los alumnos del sistema
      * Con maestroId: devuelve alumnos de ese maestro específico
    
    - Si role === 'maestro' (id_rol=2):
      * Devuelve solo los alumnos asignados al maestro autenticado
      * El parámetro maestroId es ignorado
    
    Incluye datos del alumno (nombre, apellido, email, foto, días, franja horaria, motivo de oración).
    """
    
    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 2. Obtener roles del usuario autenticado
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    
    # 3. Verificar que tenga rol de pastor o maestro
    es_pastor = 1 in roles
    es_maestro = 2 in roles
    
    if not es_pastor and not es_maestro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este recurso"
        )
    
    # 4. Lógica según el rol
    alumnos_data = []
    
    if es_pastor:
        # Pastor puede ver todos los alumnos o filtrar por maestro
        if maestroId:
            # Filtrar por maestro específico
            maestro = db.query(Maestro).filter(Maestro.id_persona == maestroId).first()
            if not maestro:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Maestro con id_persona={maestroId} no encontrado"
                )
            
            # Obtener tarjetas del maestro específico
            tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == maestro.id_maestro).all()
        else:
            # Devolver TODOS los alumnos del sistema
            tarjetas = db.query(Tarjeta).all()
    
    else:  # es_maestro
        # Maestro solo ve sus alumnos asignados
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene registro de maestro en el sistema"
            )
        
        # Obtener tarjetas asignadas a este maestro
        tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == maestro.id_maestro).all()
    
    # 5. Construir respuesta con datos de cada alumno
    for tarjeta in tarjetas:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == tarjeta.id_alumno).first()
        if not alumno:
            continue
            
        persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno.id_persona).first()
        if not persona_alumno:
            continue
        
        # Obtener datos del maestro asignado
        maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro_asignado).first()
        persona_maestro = None
        if maestro_asignado:
            persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_asignado.id_persona).first()
        
        alumnos_data.append({
            "id_alumno": str(alumno.id_alumno),
            "id_tarjeta": str(tarjeta.id_tarjeta),
            "nombre": persona_alumno.nombre,
            "apellido": persona_alumno.apellido,
            "email": persona_alumno.email,
            "foto_url": persona_alumno.foto_url,
            "dias": alumno.dias,
            "franja_horaria": alumno.franja_horaria,
            "motivo_oracion": alumno.motivo_oracion,
            "created_at": alumno.created_at.isoformat() if alumno.created_at else None,
            "maestro_asignado": {
                "id_maestro": str(maestro_asignado.id_maestro) if maestro_asignado else None,
                "nombre": persona_maestro.nombre if persona_maestro else None,
                "apellido": persona_maestro.apellido if persona_maestro else None,
                "telefono": maestro_asignado.telefono if maestro_asignado else None,
                "direccion": maestro_asignado.direccion if maestro_asignado else None
            } if maestro_asignado else None
        })
    
    return {
        "alumnos": alumnos_data,
        "total": len(alumnos_data),
        "usuario": {
            "es_pastor": es_pastor,
            "es_maestro": es_maestro,
            "filtro_maestro": maestroId if es_pastor and maestroId else None
        }
    }


@router.get("/{id_alumno}")
def get_alumno_by_id(
    id_alumno: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Obtiene un alumno específico por su ID.
    
    - Si role === 'pastor' (id_rol=1):
      * Puede ver cualquier alumno del sistema
    
    - Si role === 'maestro' (id_rol=2):
      * Solo puede ver alumnos que le estén asignados
    
    Retorna información completa del alumno incluyendo datos del maestro asignado.
    """
    
    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 2. Obtener roles del usuario autenticado
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    
    # 3. Verificar que tenga rol de pastor o maestro
    es_pastor = 1 in roles
    es_maestro = 2 in roles
    
    if not es_pastor and not es_maestro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para acceder a este recurso"
        )
    
    # 4. Buscar el alumno por ID
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alumno con id {id_alumno} no encontrado"
        )
    
    # 5. Obtener la tarjeta del alumno para verificar permisos
    tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == id_alumno).first()
    if not tarjeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información de asignación para este alumno"
        )
    
    # 6. Si es maestro, verificar que el alumno le esté asignado
    if es_maestro and not es_pastor:
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene registro de maestro en el sistema"
            )
        
        if tarjeta.id_maestro_asignado != maestro.id_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para ver este alumno"
            )
    
    # 7. Obtener datos de la persona del alumno
    persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno.id_persona).first()
    if not persona_alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información personal del alumno"
        )
    
    # 8. Obtener datos del maestro asignado
    maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro_asignado).first()
    persona_maestro = None
    if maestro_asignado:
        persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_asignado.id_persona).first()
    
    # 9. Construir respuesta
    return {
        "id_alumno": str(alumno.id_alumno),
        "id_tarjeta": str(tarjeta.id_tarjeta),
        "nombre": persona_alumno.nombre,
        "apellido": persona_alumno.apellido,
        "email": persona_alumno.email,
        "foto_url": persona_alumno.foto_url,
        "dias": alumno.dias,
        "franja_horaria": alumno.franja_horaria,
        "motivo_oracion": alumno.motivo_oracion,
        "created_at": alumno.created_at.isoformat() if alumno.created_at else None,
        "maestro_asignado": {
            "id_maestro": str(maestro_asignado.id_maestro) if maestro_asignado else None,
            "nombre": persona_maestro.nombre if persona_maestro else None,
            "apellido": persona_maestro.apellido if persona_maestro else None,
            "telefono": maestro_asignado.telefono if maestro_asignado else None,
            "direccion": maestro_asignado.direccion if maestro_asignado else None
        } if maestro_asignado else None
    }


@router.put("/{id_alumno}")
def update_alumno(
    id_alumno: str,
    alumno_data: AlumnoUpdate,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Actualiza la información de un alumno específico.
    
    - Si role === 'pastor' (id_rol=1):
      * Puede actualizar cualquier alumno del sistema
    
    - Si role === 'maestro' (id_rol=2):
      * Solo puede actualizar alumnos que le estén asignados
    
    Los campos que se pueden actualizar son:
    - Datos personales: nombre, apellido, email, foto_url
    - Datos de alumno: dias, franja_horaria, motivo_oracion
    
    Todos los campos son opcionales, solo se actualizan los que se envían.
    """
    
    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 2. Obtener roles del usuario autenticado
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    
    # 3. Verificar que tenga rol de pastor o maestro
    es_pastor = 1 in roles
    es_maestro = 2 in roles
    
    if not es_pastor and not es_maestro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para actualizar alumnos"
        )
    
    # 4. Buscar el alumno por ID
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alumno con id {id_alumno} no encontrado"
        )
    
    # 5. Obtener la tarjeta del alumno para verificar permisos
    tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == id_alumno).first()
    if not tarjeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información de asignación para este alumno"
        )
    
    # 6. Si es maestro, verificar que el alumno le esté asignado
    if es_maestro and not es_pastor:
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no tiene registro de maestro en el sistema"
            )
        
        if tarjeta.id_maestro_asignado != maestro.id_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para actualizar este alumno"
            )
    
    # 7. Obtener la persona relacionada con el alumno
    persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno.id_persona).first()
    if not persona_alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información personal del alumno"
        )
    
    # 8. Actualizar los campos de Persona (si se proporcionan)
    update_data = alumno_data.model_dump(exclude_unset=True)
    
    if "nombre" in update_data:
        persona_alumno.nombre = update_data["nombre"]
    if "apellido" in update_data:
        persona_alumno.apellido = update_data["apellido"]
    if "email" in update_data:
        persona_alumno.email = update_data["email"]
    if "foto_url" in update_data:
        persona_alumno.foto_url = update_data["foto_url"]
    
    # 9. Actualizar los campos de Alumno (si se proporcionan)
    if "dias" in update_data:
        alumno.dias = update_data["dias"]
    if "franja_horaria" in update_data:
        alumno.franja_horaria = update_data["franja_horaria"]
    if "motivo_oracion" in update_data:
        alumno.motivo_oracion = update_data["motivo_oracion"]
    
    # 10. Guardar cambios en la base de datos
    try:
        db.commit()
        db.refresh(alumno)
        db.refresh(persona_alumno)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el alumno: {str(e)}"
        )
    
    # 11. Obtener datos del maestro asignado para la respuesta
    maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro_asignado).first()
    persona_maestro = None
    if maestro_asignado:
        persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_asignado.id_persona).first()
    
    # 12. Construir y retornar respuesta
    return {
        "message": "Alumno actualizado exitosamente",
        "alumno": {
            "id_alumno": str(alumno.id_alumno),
            "id_tarjeta": str(tarjeta.id_tarjeta),
            "nombre": persona_alumno.nombre,
            "apellido": persona_alumno.apellido,
            "email": persona_alumno.email,
            "foto_url": persona_alumno.foto_url,
            "dias": alumno.dias,
            "franja_horaria": alumno.franja_horaria,
            "motivo_oracion": alumno.motivo_oracion,
            "created_at": alumno.created_at.isoformat() if alumno.created_at else None,
            "maestro_asignado": {
                "id_maestro": str(maestro_asignado.id_maestro) if maestro_asignado else None,
                "nombre": persona_maestro.nombre if persona_maestro else None,
                "apellido": persona_maestro.apellido if persona_maestro else None,
                "telefono": maestro_asignado.telefono if maestro_asignado else None,
                "direccion": maestro_asignado.direccion if maestro_asignado else None
            } if maestro_asignado else None
        }
    }
