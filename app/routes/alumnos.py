from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.persona import Persona
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.tarjeta import Tarjeta

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])

@router.get("")
def get_alumnos_by_maestro(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    maestroId: Optional[str] = Query(None, description="ID de persona del maestro para filtrar alumnos")
):
    """
    Obtiene todos los alumnos asignados a un maestro.
    
    - Si se proporciona `maestroId`: Retorna alumnos de ese maestro específico (requiere ser pastor).
    - Si NO se proporciona `maestroId`: Retorna alumnos del maestro autenticado.
    
    Incluye datos del alumno (nombre, apellido, email, foto) y dirección del maestro.
    """
    
    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 2. Determinar qué maestro consultar
    if maestroId:
        # Si se proporciona maestroId, verificar que el usuario autenticado sea pastor (id_rol=1)
        if persona_autenticada.id_rol != 1:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo los pastores pueden consultar alumnos de otros maestros"
            )
        
        # Buscar el maestro por id_persona
        maestro = db.query(Maestro).filter(Maestro.id_persona == maestroId).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Maestro con id_persona={maestroId} no encontrado"
            )
        
        # Obtener datos de la persona del maestro consultado
        persona_maestro = db.query(Persona).filter(Persona.id_persona == maestroId).first()
    else:
        # Si no se proporciona maestroId, usar el maestro autenticado
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario no es un maestro"
            )
        persona_maestro = persona_autenticada
    
    # 3. Obtener todas las tarjetas asignadas a este maestro
    tarjetas = (
        db.query(Tarjeta)
        .filter(Tarjeta.id_maestro_asignado == maestro.id_maestro)
        .all()
    )
    
    # 4. Construir respuesta con datos de cada alumno
    alumnos_data = []
    for tarjeta in tarjetas:
        alumno = db.query(Alumno).filter(Alumno.id_alumno == tarjeta.id_alumno).first()
        if not alumno:
            continue
            
        persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno.id_persona).first()
        if not persona_alumno:
            continue
        
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
            "created_at": alumno.created_at.isoformat() if alumno.created_at else None
        })
    
    return {
        "maestro": {
            "id_maestro": str(maestro.id_maestro),
            "nombre": persona_maestro.nombre,
            "apellido": persona_maestro.apellido,
            "telefono": maestro.telefono,
            "direccion": maestro.direccion
        },
        "alumnos": alumnos_data,
        "total": len(alumnos_data)
    }