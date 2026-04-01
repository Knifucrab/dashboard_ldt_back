from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID
from typing import Optional

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.bolsa import Bolsa
from app.models.estado import Estado
from app.models.historial_estado import HistorialEstado
from app.models.persona import Persona
from app.models.profile import Profile
from app.models.alumno import Alumno
from app.models.tarjeta import Tarjeta
from app.models.maestro import Maestro
from app.models.observacion import Observacion
from app.models.person_role import PersonRole
from app.schemas.bolsa import BolsaCreate, BolsaResponse, BolsaWithEstados, BolsaUpdate, EstadoResponse

router = APIRouter(prefix="/bolsas", tags=["Bolsas"])


@router.post("", response_model=BolsaResponse, status_code=status.HTTP_201_CREATED)
def create_bolsa(
    bolsa_data: BolsaCreate,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Crea una nueva bolsa (conjunto de estados lógicos).
    
    Requiere autenticación de administrador (nivel_acceso=1).
    
    Una bolsa agrupa estados que pertenecen a un mismo contexto o ciclo
    (ej: "1er Año - 2026"). El array estados_orden se mantiene automáticamente
    por el trigger de base de datos.
    
    Args:
        bolsa_data: Datos de la bolsa (nombre, descripcion, estados)
        
    Returns:
        La bolsa creada con su id_bolsa y created_at
    """
    
    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # Verificar que sea administrador
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )

    if perfil.nivel_acceso != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden crear bolsas"
        )

    # Verificar que no exista una bolsa con el mismo nombre (case-insensitive)
    bolsa_existente = db.query(Bolsa).filter(
        func.lower(Bolsa.nombre) == bolsa_data.nombre.lower()
    ).first()
    
    if bolsa_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una bolsa con el nombre '{bolsa_data.nombre}'"
        )

    # Crear la nueva bolsa
    nueva_bolsa = Bolsa(
        nombre=bolsa_data.nombre,
        descripcion=bolsa_data.descripcion
    )
    
    db.add(nueva_bolsa)
    db.commit()
    db.refresh(nueva_bolsa)

    # Crear los estados y asociarlos a la bolsa
    if bolsa_data.estados:
        # Obtener el último orden de estados para continuar la secuencia
        max_orden = db.query(func.max(Estado.orden)).scalar() or 0
        
        for idx, nombre_estado in enumerate(bolsa_data.estados, start=1):
            # Verificar si el estado ya existe
            estado_existente = db.query(Estado).filter(
                func.lower(Estado.nombre) == nombre_estado.lower()
            ).first()
            
            if estado_existente:
                # Si existe, solo asociarlo a la bolsa
                estado_existente.id_bolsa = nueva_bolsa.id_bolsa
            else:
                # Si no existe, crearlo
                nuevo_estado = Estado(
                    nombre=nombre_estado,
                    orden=max_orden + idx,
                    activo=True,
                    id_bolsa=nueva_bolsa.id_bolsa
                )
                db.add(nuevo_estado)
        
        db.commit()
        db.refresh(nueva_bolsa)

    return nueva_bolsa


@router.put("/{id_bolsa}", response_model=BolsaResponse)
def update_bolsa(
    id_bolsa: str,
    bolsa_data: BolsaUpdate,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Actualiza una bolsa existente.
    
    Requiere autenticación de administrador (nivel_acceso=1).
    
    Permite actualizar el nombre, descripción y los estados asociados
    de una bolsa. Si se proporcionan estados_ids, se reemplazarán todos los estados
    anteriores por los nuevos.
    
    Args:
        id_bolsa: UUID de la bolsa a actualizar
        bolsa_data: Datos a actualizar (nombre, descripcion, estados)
        
    Returns:
        La bolsa actualizada
    """
    
    # Convertir el id_bolsa a UUID
    try:
        bolsa_uuid = UUID(id_bolsa)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de bolsa inválido. Debe ser un UUID válido"
        )
    
    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # Verificar que sea administrador
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )

    if perfil.nivel_acceso != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden actualizar bolsas"
        )

    # Buscar la bolsa
    bolsa = db.query(Bolsa).filter(Bolsa.id_bolsa == bolsa_uuid).first()
    if not bolsa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bolsa con id {id_bolsa} no encontrada"
        )

    # Verificar que no exista otra bolsa con el mismo nombre (si se está cambiando el nombre)
    if bolsa_data.nombre and bolsa_data.nombre.lower() != bolsa.nombre.lower():
        bolsa_existente = db.query(Bolsa).filter(
            func.lower(Bolsa.nombre) == bolsa_data.nombre.lower()
        ).first()
        
        if bolsa_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ya existe una bolsa con el nombre '{bolsa_data.nombre}'"
            )

    # Actualizar campos básicos
    if bolsa_data.nombre is not None:
        bolsa.nombre = bolsa_data.nombre
    if bolsa_data.descripcion is not None:
        bolsa.descripcion = bolsa_data.descripcion

    # Actualizar estados asociados si se proporcionaron
    if bolsa_data.estados is not None:
        # Primero, desvincular todos los estados actuales de esta bolsa
        estados_actuales = db.query(Estado).filter(Estado.id_bolsa == bolsa.id_bolsa).all()
        for estado in estados_actuales:
            estado.id_bolsa = None
        
        # Obtener el último orden de estados para continuar la secuencia
        max_orden = db.query(func.max(Estado.orden)).scalar() or 0
        
        # Luego, crear o asociar los nuevos estados
        for idx, nombre_estado in enumerate(bolsa_data.estados, start=1):
            # Verificar si el estado ya existe
            estado_existente = db.query(Estado).filter(
                func.lower(Estado.nombre) == nombre_estado.lower()
            ).first()
            
            if estado_existente:
                # Si existe, solo asociarlo a la bolsa
                estado_existente.id_bolsa = bolsa.id_bolsa
            else:
                # Si no existe, crearlo
                nuevo_estado = Estado(
                    nombre=nombre_estado,
                    orden=max_orden + idx,
                    activo=True,
                    id_bolsa=bolsa.id_bolsa
                )
                db.add(nuevo_estado)
    
    db.commit()
    db.refresh(bolsa)

    return bolsa


@router.get("", response_model=list[BolsaWithEstados])
def get_bolsas(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Lista todas las bolsas del sistema.
    
    Requiere autenticación.
        
    Returns:
        Lista de bolsas con conteo de estados totales y activos
    """
    
    # Verificar que el usuario autenticado exista
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    bolsas = db.query(Bolsa).all()
    
    # Enriquecer con información de estados
    result = []
    for bolsa in bolsas:
        estados = db.query(Estado).filter(
            Estado.id_bolsa == bolsa.id_bolsa
        ).order_by(Estado.orden).all()

        result.append({
            "id_bolsa": bolsa.id_bolsa,
            "nombre": bolsa.nombre,
            "descripcion": bolsa.descripcion,
            "estados_orden": bolsa.estados_orden,
            "created_at": bolsa.created_at,
            "total_estados": len(estados),
            "estados_activos": sum(1 for e in estados if e.activo),
            "estados": [
                {"id_estado": e.id_estado, "nombre": e.nombre, "orden": e.orden, "activo": e.activo}
                for e in estados
            ]
        })
    
    return result


@router.get("/{id_bolsa}/alumnos")
def get_alumnos_por_bolsa(
    id_bolsa: UUID,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    id_estado: Optional[int] = Query(None, description="Filtrar por un estado específico de la bolsa")
):
    """
    Devuelve todos los alumnos agrupados por estado para una bolsa dada.

    - id_bolsa: UUID de la bolsa
    - id_estado (opcional): filtra y devuelve solo el estado indicado

    Flujo: Bolsa → estados de la bolsa → alumnos cuyo id_estado_actual coincide.
    Incluye datos del maestro asignado desde la tabla tarjetas.
    """

    # 1. Verificar usuario autenticado
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # 2. Verificar que la bolsa existe
    bolsa = db.query(Bolsa).filter(Bolsa.id_bolsa == id_bolsa).first()
    if not bolsa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bolsa con id {id_bolsa} no encontrada"
        )

    # 3. Obtener estados de la bolsa, ordenados por campo orden
    query_estados = db.query(Estado).filter(Estado.id_bolsa == id_bolsa)

    if id_estado is not None:
        # Validar que ese estado pertenece a la bolsa
        estado_filtro = query_estados.filter(Estado.id_estado == id_estado).first()
        if not estado_filtro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El estado {id_estado} no pertenece a la bolsa {id_bolsa}"
            )
        estados = [estado_filtro]
    else:
        estados = query_estados.order_by(Estado.orden).all()

    # 4. Para cada estado, buscar alumnos cuyo id_estado_actual coincida
    estados_con_alumnos = []
    for estado in estados:
        alumnos = db.query(Alumno).filter(Alumno.id_estado_actual == estado.id_estado).all()

        alumnos_data = []
        for alumno in alumnos:
            persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno.id_persona).first()
            if not persona_alumno:
                continue

            # Obtener tarjeta y maestro asignado
            tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == alumno.id_alumno).first()
            maestro_data = None
            if tarjeta and tarjeta.id_maestro_asignado:
                maestro = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro_asignado).first()
                if maestro:
                    persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro.id_persona).first()
                    maestro_data = {
                        "id_maestro": str(maestro.id_maestro),
                        "nombre": persona_maestro.nombre if persona_maestro else None,
                        "apellido": persona_maestro.apellido if persona_maestro else None,
                        "telefono": maestro.telefono,
                        "direccion": maestro.direccion
                    }

            alumnos_data.append({
                "id_alumno": str(alumno.id_alumno),
                "nombre": persona_alumno.nombre,
                "apellido": persona_alumno.apellido,
                "email": persona_alumno.email,
                "foto_url": persona_alumno.foto_url,
                "dias": alumno.dias,
                "franja_horaria": alumno.franja_horaria,
                "motivo_oracion": alumno.motivo_oracion,
                "maestro_asignado": maestro_data
            })

        estados_con_alumnos.append({
            "id_estado": estado.id_estado,
            "nombre": estado.nombre,
            "orden": estado.orden,
            "total_alumnos": len(alumnos_data),
            "alumnos": alumnos_data
        })

    return {
        "id_bolsa": str(bolsa.id_bolsa),
        "nombre": bolsa.nombre,
        "descripcion": bolsa.descripcion,
        "estados": estados_con_alumnos
    }


@router.get("/maestro/{id_maestro}")
def get_bolsas_por_maestro(
    id_maestro: UUID,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Devuelve las bolsas donde el maestro tiene alumnos asignados.

    Para cada bolsa se listan TODOS sus estados con la cantidad de alumnos
    asignados a ese maestro en cada estado (puede ser 0).

    - id_maestro: UUID del maestro
    """

    # 1. Verificar usuario autenticado
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # 2. Verificar que el maestro existe
    maestro = db.query(Maestro).filter(Maestro.id_maestro == id_maestro).first()
    if not maestro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maestro con id {id_maestro} no encontrado"
        )

    # 3. Obtener todos los alumnos asignados a este maestro via tarjetas
    tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == id_maestro).all()
    if not tarjetas:
        return []

    alumno_ids = [t.id_alumno for t in tarjetas]

    # 4. Obtener id_estado_actual de esos alumnos y contar por estado
    alumnos = db.query(Alumno).filter(Alumno.id_alumno.in_(alumno_ids)).all()

    # Mapa: id_estado → cantidad de alumnos de este maestro en ese estado
    conteo_por_estado: dict[int, int] = {}
    for alumno in alumnos:
        eid = alumno.id_estado_actual
        conteo_por_estado[eid] = conteo_por_estado.get(eid, 0) + 1

    # 5. Obtener los estados que tienen alumnos de este maestro
    estado_ids_con_alumnos = list(conteo_por_estado.keys())
    estados_con_alumnos = db.query(Estado).filter(
        Estado.id_estado.in_(estado_ids_con_alumnos)
    ).all()

    # 6. Determinar las bolsas afectadas (solo las que tienen al menos un alumno de este maestro)
    bolsa_ids = list({e.id_bolsa for e in estados_con_alumnos if e.id_bolsa is not None})
    if not bolsa_ids:
        return []

    bolsas = db.query(Bolsa).filter(Bolsa.id_bolsa.in_(bolsa_ids)).all()

    # 7. Para cada bolsa obtener TODOS sus estados y adjuntar el conteo
    result = []
    for bolsa in bolsas:
        todos_estados = db.query(Estado).filter(
            Estado.id_bolsa == bolsa.id_bolsa
        ).order_by(Estado.orden).all()

        estados_data = [
            {
                "id_estado": estado.id_estado,
                "nombre": estado.nombre,
                "orden": estado.orden,
                "activo": estado.activo,
                "total_alumnos": conteo_por_estado.get(estado.id_estado, 0)
            }
            for estado in todos_estados
        ]

        result.append({
            "id_bolsa": str(bolsa.id_bolsa),
            "nombre": bolsa.nombre,
            "descripcion": bolsa.descripcion,
            "estados": estados_data
        })

    return result


@router.delete("/{id_bolsa}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bolsa(
    id_bolsa: UUID,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Elimina una bolsa y todo su contenido en cascada:
    estados → historial_estados, tarjetas (y alumnos relacionados).

    Requiere autenticación de administrador (nivel_acceso=1).
    """

    # Verificar usuario autenticado
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # Verificar que sea administrador
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil or perfil.nivel_acceso != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden eliminar bolsas"
        )

    # Verificar que la bolsa exista
    bolsa = db.query(Bolsa).filter(Bolsa.id_bolsa == id_bolsa).first()
    if not bolsa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bolsa no encontrada"
        )

    # 1. Obtener IDs de los estados de esta bolsa
    estado_ids = [
        e.id_estado for e in
        db.query(Estado.id_estado).filter(Estado.id_bolsa == id_bolsa).all()
    ]

    try:
        if estado_ids:
            # 2. Obtener alumnos cuyo estado actual pertenece a esta bolsa.
            #    Se usa Alumno.id_estado_actual directamente porque no tiene FK y no
            #    se borra en cascada automáticamente desde la BD.
            alumnos = db.query(Alumno.id_alumno, Alumno.id_persona).filter(
                Alumno.id_estado_actual.in_(estado_ids)
            ).all()
            alumno_ids = [a.id_alumno for a in alumnos]
            persona_ids = [a.id_persona for a in alumnos]

            if alumno_ids:
                # 3. Borrar observaciones (FK id_alumno CASCADE, explícito para evitar
                #    conflicto con id_autor RESTRICT al borrar personas más adelante)
                db.query(Observacion).filter(
                    Observacion.id_alumno.in_(alumno_ids)
                ).delete(synchronize_session=False)

                # 4. Borrar historial de esos alumnos
                db.query(HistorialEstado).filter(
                    HistorialEstado.id_alumno.in_(alumno_ids)
                ).delete(synchronize_session=False)

                # 5. Borrar tarjetas (FK id_alumno + id_estado_actual, ambas con CASCADE en BD)
                db.query(Tarjeta).filter(
                    Tarjeta.id_alumno.in_(alumno_ids)
                ).delete(synchronize_session=False)

                # 6. Borrar alumnos
                db.query(Alumno).filter(
                    Alumno.id_alumno.in_(alumno_ids)
                ).delete(synchronize_session=False)

            if persona_ids:
                # 7a. Anular cambiado_por en historial_estados que apunte a estas personas.
                #     La columna no tiene ondelete, por defecto es NO ACTION → bloquea el DELETE.
                db.query(HistorialEstado).filter(
                    HistorialEstado.cambiado_por.in_(persona_ids)
                ).update({HistorialEstado.cambiado_por: None}, synchronize_session=False)

                # 7b. Borrar observaciones donde estas personas son el autor (id_autor RESTRICT).
                #     El paso 3 ya borró las observaciones de los alumnos de esta bolsa,
                #     pero estas personas pueden haber escrito observaciones para otros alumnos.
                db.query(Observacion).filter(
                    Observacion.id_autor.in_(persona_ids)
                ).delete(synchronize_session=False)

                # 8. Borrar roles de esas personas (FK person_id CASCADE)
                db.query(PersonRole).filter(
                    PersonRole.person_id.in_(persona_ids)
                ).delete(synchronize_session=False)

                # 9. Borrar personas
                db.query(Persona).filter(
                    Persona.id_persona.in_(persona_ids)
                ).delete(synchronize_session=False)

            # 10. Borrar cualquier historial que aún apunte a estos estados (de otros alumnos)
            db.query(HistorialEstado).filter(
                HistorialEstado.id_estado.in_(estado_ids)
            ).delete(synchronize_session=False)

            # 11. Borrar tarjetas restantes que apunten a estos estados
            db.query(Tarjeta).filter(
                Tarjeta.id_estado_actual.in_(estado_ids)
            ).delete(synchronize_session=False)

            # 12. Borrar los estados
            db.query(Estado).filter(
                Estado.id_bolsa == id_bolsa
            ).delete(synchronize_session=False)

        # 13. Borrar la bolsa
        db.query(Bolsa).filter(Bolsa.id_bolsa == id_bolsa).delete(synchronize_session=False)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar bolsa: {str(e)}"
        )
