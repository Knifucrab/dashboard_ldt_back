"""
Endpoint global de actividad: muestra el historial de cambios de estado
y las observaciones/comentarios de todos los alumnos, ordenados por fecha.

Permisos:
- Administrador (nivel_acceso=1): ve la actividad de TODOS los alumnos.
- Pastor (id_rol=1): ve la actividad de TODOS los alumnos.
- Maestro (id_rol=2): ve solo la actividad de sus alumnos asignados.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Optional

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.persona import Persona
from app.models.person_role import PersonRole
from app.models.profile import Profile
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.tarjeta import Tarjeta
from app.models.estado import Estado
from app.models.historial_estado import HistorialEstado
from app.models.observacion import Observacion

router = APIRouter(prefix="/actividad", tags=["Actividad"])


@router.get("")
def get_actividad_global(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limite: int = Query(50, ge=1, le=200, description="Cantidad máxima de eventos a devolver"),
    tipo: Optional[str] = Query(
        None,
        description="Filtrar por tipo: 'cambio_estado' | 'observacion'. Omitir para ambos.",
    ),
):
    """
    Devuelve un feed global de actividad mezclando cambios de estado y
    observaciones/comentarios, ordenados del más reciente al más antiguo.

    Cada evento incluye el campo **tipo**:
    - `cambio_estado`: se cambió el estado de un alumno (quién lo cambió, a qué estado, comentario opcional).
    - `observacion`: un maestro o pastor dejó un comentario sobre un alumno.

    El campo **limite** (máx. 200) controla cuántos eventos se devuelven.
    El campo **tipo** permite filtrar solo cambios de estado u observaciones.
    """

    # 1. Obtener persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    # 2. Obtener perfil
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")

    es_admin = perfil.nivel_acceso == 1

    # 3. Determinar qué alumnos puede ver el usuario
    if es_admin:
        # Admin ve todos los alumnos
        alumnos_ids = [str(a.id_alumno) for a in db.query(Alumno.id_alumno).all()]
    else:
        person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
        roles = [pr.id_rol for pr in person_roles]
        es_pastor = 1 in roles
        es_maestro = 2 in roles

        if not es_pastor and not es_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para ver la actividad",
            )

        if es_pastor:
            # Pastor ve todos los alumnos
            alumnos_ids = [str(a.id_alumno) for a in db.query(Alumno.id_alumno).all()]
        else:
            # Maestro ve solo sus alumnos
            maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
            if not maestro:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario no tiene registro de maestro en el sistema",
                )
            tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == maestro.id_maestro).all()
            alumnos_ids = [str(t.id_alumno) for t in tarjetas]

    if not alumnos_ids:
        return {"total": 0, "actividad": []}

    eventos = []

    # 4a. Cambios de estado
    if tipo in (None, "cambio_estado"):
        historial = (
            db.query(HistorialEstado)
            .filter(HistorialEstado.id_alumno.in_(alumnos_ids))
            .all()
        )
        for reg in historial:
            alumno_obj = db.query(Alumno).filter(Alumno.id_alumno == reg.id_alumno).first()
            persona_alumno = (
                db.query(Persona).filter(Persona.id_persona == alumno_obj.id_persona).first()
                if alumno_obj
                else None
            )
            estado_obj = db.query(Estado).filter(Estado.id_estado == reg.id_estado).first()
            autor_obj = (
                db.query(Persona).filter(Persona.id_persona == reg.cambiado_por).first()
                if reg.cambiado_por
                else None
            )
            eventos.append(
                {
                    "tipo": "cambio_estado",
                    "fecha": reg.fecha_cambio,
                    "id_referencia": str(reg.id_historial),
                    "alumno": {
                        "id_alumno": str(reg.id_alumno),
                        "nombre": persona_alumno.nombre if persona_alumno else None,
                        "apellido": persona_alumno.apellido if persona_alumno else None,
                    },
                    "estado_nombre": estado_obj.nombre if estado_obj else None,
                    "comentario": reg.comentario,
                    "autor": {
                        "id_persona": str(autor_obj.id_persona) if autor_obj else None,
                        "nombre": autor_obj.nombre if autor_obj else None,
                        "apellido": autor_obj.apellido if autor_obj else None,
                    },
                }
            )

    # 4b. Observaciones / comentarios
    if tipo in (None, "observacion"):
        observaciones = (
            db.query(Observacion)
            .filter(Observacion.id_alumno.in_(alumnos_ids))
            .all()
        )
        for obs in observaciones:
            alumno_obj = db.query(Alumno).filter(Alumno.id_alumno == obs.id_alumno).first()
            persona_alumno = (
                db.query(Persona).filter(Persona.id_persona == alumno_obj.id_persona).first()
                if alumno_obj
                else None
            )
            autor_obj = db.query(Persona).filter(Persona.id_persona == obs.id_autor).first()
            eventos.append(
                {
                    "tipo": "observacion",
                    "fecha": obs.created_at,
                    "id_referencia": str(obs.id_observacion),
                    "alumno": {
                        "id_alumno": str(obs.id_alumno),
                        "nombre": persona_alumno.nombre if persona_alumno else None,
                        "apellido": persona_alumno.apellido if persona_alumno else None,
                    },
                    "texto": obs.texto,
                    "autor": {
                        "id_persona": str(autor_obj.id_persona) if autor_obj else None,
                        "nombre": autor_obj.nombre if autor_obj else None,
                        "apellido": autor_obj.apellido if autor_obj else None,
                    },
                }
            )

    # 5. Ordenar por fecha descendente y aplicar límite
    eventos.sort(key=lambda e: e["fecha"], reverse=True)
    eventos = eventos[:limite]

    # 6. Serializar fechas
    for e in eventos:
        e["fecha"] = e["fecha"].isoformat()

    return {"total": len(eventos), "actividad": eventos}
