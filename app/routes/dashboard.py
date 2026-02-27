"""
Endpoints del Dashboard.

- GET /dashboard/stats              → estadísticas generales (solo pastor/admin)
- GET /dashboard/maestro/{id}/stats → estadísticas de un maestro específico
- GET /dashboard/actividad-reciente → actividad reciente del sistema
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

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

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

def _get_persona_y_perfil(auth_user_id: str, db: Session):
    persona = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")
    perfil = db.query(Profile).filter(Profile.id_perfil == persona.id_perfil).first()
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    return persona, perfil


def _es_pastor_o_admin(persona: Persona, perfil, db: Session) -> bool:
    if perfil.nivel_acceso == 1:
        return True
    roles = [pr.id_rol for pr in db.query(PersonRole).filter(PersonRole.person_id == persona.id_persona).all()]
    return 1 in roles  # id_rol=1 → pastor


def _alumnos_por_estado(alumno_ids: list, db: Session) -> list:
    """Devuelve la distribución de alumnos por estado."""
    if not alumno_ids:
        return []

    alumnos = db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()
    conteo: dict[int, int] = {}
    for alumno in alumnos:
        if alumno.id_estado_actual is not None:
            conteo[alumno.id_estado_actual] = conteo.get(alumno.id_estado_actual, 0) + 1

    resultado = []
    for id_estado, cantidad in conteo.items():
        estado_obj = db.query(Estado).filter(Estado.id_estado == id_estado).first()
        resultado.append({
            "id_estado": id_estado,
            "estado_nombre": estado_obj.nombre if estado_obj else None,
            "cantidad": cantidad,
        })

    resultado.sort(key=lambda x: x["id_estado"])
    return resultado


# ---------------------------------------------------------------------------
# GET /dashboard/stats  –  estadísticas generales (solo pastor/admin)
# ---------------------------------------------------------------------------

@router.get("/stats")
def get_stats_generales(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve estadísticas generales del sistema.
    Solo accesible para pastores y administradores.

    Incluye:
    - total_maestros
    - total_alumnos
    - distribucion_por_estado: cuántos alumnos hay en cada estado
    - total_observaciones: comentarios escritos en total
    - total_cambios_estado: cambios de estado registrados en total
    """
    persona, perfil = _get_persona_y_perfil(auth_user_id, db)

    if not _es_pastor_o_admin(persona, perfil, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo pastores y administradores pueden ver las estadísticas generales",
        )

    total_maestros = db.query(func.count(Maestro.id_maestro)).scalar()
    total_alumnos = db.query(func.count(Alumno.id_alumno)).scalar()
    total_observaciones = db.query(func.count(Observacion.id_observacion)).scalar()
    total_cambios_estado = db.query(func.count(HistorialEstado.id_historial)).scalar()

    todos_los_alumnos_ids = [str(a.id_alumno) for a in db.query(Alumno.id_alumno).all()]
    distribucion = _alumnos_por_estado(todos_los_alumnos_ids, db)

    return {
        "total_maestros": total_maestros,
        "total_alumnos": total_alumnos,
        "total_observaciones": total_observaciones,
        "total_cambios_estado": total_cambios_estado,
        "distribucion_por_estado": distribucion,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/maestro/{id}/stats  –  estadísticas de un maestro
# ---------------------------------------------------------------------------

@router.get("/maestro/{id_maestro}/stats")
def get_stats_maestro(
    id_maestro: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve estadísticas específicas de un maestro.

    - Pastor/Admin: puede consultar cualquier maestro.
    - Maestro: solo puede consultar sus propias estadísticas.

    Incluye:
    - Info del maestro (nombre, apellido, teléfono)
    - total_alumnos_asignados
    - distribucion_por_estado de sus alumnos
    - total_observaciones escritas por el maestro
    - total_cambios_estado realizados por el maestro
    - alumno_mas_reciente: el último alumno asignado
    """
    persona, perfil = _get_persona_y_perfil(auth_user_id, db)

    es_admin_o_pastor = _es_pastor_o_admin(persona, perfil, db)

    # Si no es admin/pastor, verificar que solo consulte sus propias stats
    if not es_admin_o_pastor:
        maestro_propio = db.query(Maestro).filter(Maestro.id_persona == persona.id_persona).first()
        if not maestro_propio or str(maestro_propio.id_maestro) != id_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo puedes consultar tus propias estadísticas",
            )

    # Obtener el maestro solicitado
    maestro = db.query(Maestro).filter(Maestro.id_maestro == id_maestro).first()
    if not maestro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maestro con id {id_maestro} no encontrado",
        )

    persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro.id_persona).first()

    # Alumnos asignados al maestro
    tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == maestro.id_maestro).all()
    alumnos_ids = [str(t.id_alumno) for t in tarjetas]
    total_alumnos = len(alumnos_ids)

    distribucion = _alumnos_por_estado(alumnos_ids, db)

    # Observaciones escritas por el maestro
    total_observaciones = (
        db.query(func.count(Observacion.id_observacion))
        .filter(Observacion.id_autor == maestro.id_persona)
        .scalar()
    )

    # Cambios de estado realizados por el maestro
    total_cambios_estado = (
        db.query(func.count(HistorialEstado.id_historial))
        .filter(HistorialEstado.cambiado_por == maestro.id_persona)
        .scalar()
    )

    # Alumno más reciente
    alumno_reciente = None
    if alumnos_ids:
        alumno_obj = (
            db.query(Alumno)
            .filter(Alumno.id_alumno.in_(alumnos_ids))
            .order_by(Alumno.created_at.desc())
            .first()
        )
        if alumno_obj:
            persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno_obj.id_persona).first()
            alumno_reciente = {
                "id_alumno": str(alumno_obj.id_alumno),
                "nombre": persona_alumno.nombre if persona_alumno else None,
                "apellido": persona_alumno.apellido if persona_alumno else None,
                "created_at": alumno_obj.created_at.isoformat(),
            }

    return {
        "maestro": {
            "id_maestro": str(maestro.id_maestro),
            "nombre": persona_maestro.nombre if persona_maestro else None,
            "apellido": persona_maestro.apellido if persona_maestro else None,
            "telefono": maestro.telefono,
        },
        "total_alumnos_asignados": total_alumnos,
        "distribucion_por_estado": distribucion,
        "total_observaciones_escritas": total_observaciones,
        "total_cambios_estado_realizados": total_cambios_estado,
        "alumno_mas_reciente": alumno_reciente,
    }


# ---------------------------------------------------------------------------
# GET /dashboard/actividad-reciente  –  feed de actividad reciente
# ---------------------------------------------------------------------------

@router.get("/actividad-reciente")
def get_actividad_reciente(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    limite: int = Query(10, ge=1, le=50, description="Cantidad de eventos a devolver (máx. 50)"),
):
    """
    Devuelve los últimos eventos del sistema (cambios de estado + observaciones).

    - Pastor/Admin: ve la actividad de todos los alumnos.
    - Maestro: ve solo la actividad de sus alumnos asignados.

    Cada evento tiene el campo **tipo**: `cambio_estado` | `observacion`.
    """
    persona, perfil = _get_persona_y_perfil(auth_user_id, db)

    es_admin_o_pastor = _es_pastor_o_admin(persona, perfil, db)

    # Determinar qué alumnos puede ver
    if es_admin_o_pastor:
        alumnos_ids = [str(a.id_alumno) for a in db.query(Alumno.id_alumno).all()]
    else:
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona.id_persona).first()
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

    # Cambios de estado
    for reg in db.query(HistorialEstado).filter(HistorialEstado.id_alumno.in_(alumnos_ids)).all():
        alumno_obj = db.query(Alumno).filter(Alumno.id_alumno == reg.id_alumno).first()
        persona_alumno = (
            db.query(Persona).filter(Persona.id_persona == alumno_obj.id_persona).first()
            if alumno_obj else None
        )
        estado_obj = db.query(Estado).filter(Estado.id_estado == reg.id_estado).first()
        autor_obj = (
            db.query(Persona).filter(Persona.id_persona == reg.cambiado_por).first()
            if reg.cambiado_por else None
        )
        eventos.append({
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
        })

    # Observaciones
    for obs in db.query(Observacion).filter(Observacion.id_alumno.in_(alumnos_ids)).all():
        alumno_obj = db.query(Alumno).filter(Alumno.id_alumno == obs.id_alumno).first()
        persona_alumno = (
            db.query(Persona).filter(Persona.id_persona == alumno_obj.id_persona).first()
            if alumno_obj else None
        )
        autor_obj = db.query(Persona).filter(Persona.id_persona == obs.id_autor).first()
        eventos.append({
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
        })

    # Ordenar por fecha descendente y aplicar límite
    eventos.sort(key=lambda e: e["fecha"], reverse=True)
    eventos = eventos[:limite]

    for e in eventos:
        e["fecha"] = e["fecha"].isoformat()

    return {"total": len(eventos), "actividad": eventos}
