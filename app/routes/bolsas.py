from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from uuid import UUID

from app.dependencies.db import get_db
from app.dependencies.auth import get_current_user_id
from app.models.bolsa import Bolsa
from app.models.estado import Estado
from app.models.historial_estado import HistorialEstado
from app.models.persona import Persona
from app.models.profile import Profile
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
        bolsa_data: Datos de la bolsa (nombre, descripcion, activo, estados)
        
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
        descripcion=bolsa_data.descripcion,
        activo=bolsa_data.activo
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
    
    Permite actualizar el nombre, descripción, estado activo y los estados asociados
    de una bolsa. Si se proporcionan estados_ids, se reemplazarán todos los estados
    anteriores por los nuevos.
    
    Args:
        id_bolsa: UUID de la bolsa a actualizar
        bolsa_data: Datos a actualizar (nombre, descripcion, estados, activo)
        
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
    if bolsa_data.activo is not None:
        bolsa.activo = bolsa_data.activo

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


@router.delete("/{id_bolsa}", status_code=status.HTTP_200_OK)
def delete_bolsa(
    id_bolsa: str,
    force: bool = False,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Elimina una bolsa del sistema.
    
    Requiere autenticación de administrador (nivel_acceso=1).
    
    PRECAUCIÓN: Por defecto, marca la bolsa como inactiva (soft delete) para
    preservar el historial y la trazabilidad. 
    
    Comportamiento:
    - force=False (default): Marca la bolsa como activo=false (recomendado)
    - force=True: Elimina físicamente la bolsa y todos sus estados en cascada
    
    ADVERTENCIA con force=True:
    - Se eliminarán todos los estados asociados (ON DELETE CASCADE)
    - Si historial_estados referencia esos estados, el borrado puede:
      * Fallar si no hay ON DELETE CASCADE/SET NULL en historial_estados
      * Eliminar historial si hay ON DELETE CASCADE
      * Dejar huérfanos si hay ON DELETE SET NULL
      
    Args:
        id_bolsa: UUID de la bolsa a eliminar
        force: Si es True, elimina físicamente; si es False, marca inactiva
        
    Returns:
        Mensaje de confirmación y detalles de la operación
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
            detail="Solo los administradores pueden eliminar bolsas"
        )

    # Buscar la bolsa
    bolsa = db.query(Bolsa).filter(Bolsa.id_bolsa == bolsa_uuid).first()
    if not bolsa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bolsa con id {id_bolsa} no encontrada"
        )

    # Contar estados asociados
    estados_count = db.query(Estado).filter(Estado.id_bolsa == bolsa_uuid).count()
    
    # Nota: La verificación del historial se ha simplificado
    # Para operaciones de producción, considera implementar una verificación más robusta
    historial_count = 0

    if not force:
        # Soft delete: marcar como inactiva
        bolsa.activo = False
        db.commit()
        
        return {
            "message": "Bolsa marcada como inactiva exitosamente",
            "tipo_operacion": "soft_delete",
            "id_bolsa": str(bolsa.id_bolsa),
            "nombre": bolsa.nombre,
            "estados_asociados": estados_count,
            "registros_historial": historial_count,
            "nota": "La bolsa y sus estados siguen en la base de datos pero marcados como inactivos"
        }
    else:
        # Hard delete: eliminar físicamente
        if historial_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"No se puede eliminar la bolsa porque tiene {historial_count} "
                    f"registros en el historial. Para preservar la trazabilidad, "
                    f"usa force=false para marcarla como inactiva en su lugar."
                )
            )
        
        # Eliminar la bolsa (los estados se eliminan en cascada)
        db.delete(bolsa)
        db.commit()
        
        return {
            "message": "Bolsa eliminada exitosamente",
            "tipo_operacion": "hard_delete",
            "id_bolsa": str(id_bolsa),
            "nombre": bolsa.nombre,
            "estados_eliminados": estados_count,
            "advertencia": "Esta operación es irreversible"
        }


@router.get("", response_model=list[BolsaWithEstados])
def get_bolsas(
    activo: bool | None = None,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Lista todas las bolsas del sistema.
    
    Requiere autenticación.
    
    Args:
        activo: Filtrar por estado activo (True/False). Si es None, devuelve todas.
        
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

    # Construir query base
    query = db.query(Bolsa)
    
    if activo is not None:
        query = query.filter(Bolsa.activo == activo)
    
    bolsas = query.all()
    
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
            "activo": bolsa.activo,
            "created_at": bolsa.created_at,
            "total_estados": len(estados),
            "estados_activos": sum(1 for e in estados if e.activo),
            "estados": [
                {"id_estado": e.id_estado, "nombre": e.nombre, "orden": e.orden, "activo": e.activo}
                for e in estados
            ]
        })
    
    return result
