from fastapi import APIRouter, Depends, HTTPException, status, Query, Form, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import json as json_lib
from types import SimpleNamespace

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
from app.models.bolsa import Bolsa
from app.models.observacion import Observacion
from app.schemas.alumno import CambiarEstadoAlumno
from app.schemas.observacion import ObservacionInput

router = APIRouter(prefix="/alumnos", tags=["Alumnos"])

@router.get("")
def get_alumnos(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    maestroId: Optional[str] = Query(None, description="ID de persona del maestro para filtrar alumnos (solo para pastores)")
):
    """
    Obtiene alumnos según el perfil y rol del usuario autenticado.
    
    - Si nivel_acceso === 1 (Administrador):
      * Devuelve TODOS los alumnos del sistema (sin restricciones)
    
    - Si role === 'pastor' (id_rol=1) y no es admin:
      * Sin maestroId: devuelve TODOS los alumnos del sistema
      * Con maestroId: devuelve alumnos de ese maestro específico
    
    - Si role === 'maestro' (id_rol=2) y no es admin:
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
    
    # 2. Obtener perfil del usuario
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )
    
    es_admin = perfil.nivel_acceso == 1
    
    # 3. Si es administrador, devolver todos los alumnos sin restricciones
    if es_admin:
        if maestroId:
            # Admin puede filtrar por maestro si lo desea
            maestro = db.query(Maestro).filter(Maestro.id_persona == maestroId).first()
            if not maestro:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Maestro con id_persona={maestroId} no encontrado"
                )
            tarjetas = db.query(Tarjeta).filter(Tarjeta.id_maestro_asignado == maestro.id_maestro).all()
        else:
            tarjetas = db.query(Tarjeta).all()
    else:
        # 4. Obtener roles del usuario autenticado (solo si no es admin)
        person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
        roles = [pr.id_rol for pr in person_roles]
        
        # 5. Verificar que tenga rol de pastor o maestro
        es_pastor = 1 in roles
        es_maestro = 2 in roles
        
        if not es_pastor and not es_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este recurso"
            )
        
        # 6. Lógica según el rol
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
    
    # 7. Construir respuesta con datos de cada alumno
    alumnos_data = []
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
    
    # 8. Preparar información del usuario para la respuesta
    if es_admin:
        return {
            "alumnos": alumnos_data,
            "total": len(alumnos_data),
            "usuario": {
                "es_admin": True,
                "es_pastor": False,
                "es_maestro": False,
                "filtro_maestro": maestroId if maestroId else None
            }
        }
    else:
        return {
            "alumnos": alumnos_data,
            "total": len(alumnos_data),
            "usuario": {
                "es_admin": False,
                "es_pastor": es_pastor,
                "es_maestro": es_maestro,
                "filtro_maestro": maestroId if es_pastor and maestroId else None
            }
        }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_alumno(
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    nombre: str = Form(...),
    apellido: str = Form(...),
    id_estado_actual: int = Form(...),
    email: Optional[str] = Form(None),
    franja_horaria: Optional[str] = Form(None),
    motivo_oracion: Optional[str] = Form(None),
    id_maestro: Optional[str] = Form(None),
    dias: Optional[str] = Form(None, description="JSON string con los días disponibles. Ej: '{\"lunes\":true}'"),
    foto: Optional[UploadFile] = File(None)
):
    """
    Crea un nuevo alumno y lo asigna a un maestro.
    Acepta multipart/form-data. La foto se sube a Supabase Storage.
    El campo 'dias' debe enviarse como JSON string.
    """

    # Parsear dias (JSON string -> dict)
    dias_dict = None
    if dias:
        try:
            dias_dict = json_lib.loads(dias)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El campo 'dias' debe ser un JSON válido. Ej: '{\"lunes\":true}'"
            )

    # Subir foto a Supabase Storage si se proporcionó
    foto_url = None
    if foto and foto.filename:
        from app.integrations.storage import upload_foto
        foto_url = upload_foto(foto, "alumnos")

    # Construir objeto con la misma interfaz que AlumnoCreate para reutilizar el resto del código
    alumno_data = SimpleNamespace(
        nombre=nombre,
        apellido=apellido,
        email=email,
        foto_url=foto_url,
        dias=dias_dict,
        franja_horaria=franja_horaria,
        motivo_oracion=motivo_oracion,
        id_estado_actual=id_estado_actual,
        id_maestro=id_maestro
    )
    
    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 2. Obtener perfil del usuario
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )
    
    es_admin = perfil.nivel_acceso == 1
    
    # 3. Validar que el estado existe en la tabla de estados
    estado = db.query(Estado).filter(Estado.id_estado == alumno_data.id_estado_actual).first()
    if not estado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estado con id {alumno_data.id_estado_actual} no encontrado"
        )
    
    if not estado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El estado con id {alumno_data.id_estado_actual} no está activo"
        )
    
    # 4. Determinar el maestro a asignar según el tipo de usuario
    id_maestro_asignado = None
    
    if es_admin:
        # Administrador debe proporcionar el id_maestro
        if not alumno_data.id_maestro:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Los administradores deben proporcionar id_maestro para asignar el alumno"
            )
        
        # Verificar que el maestro existe
        maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == alumno_data.id_maestro).first()
        if not maestro_asignado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Maestro con id {alumno_data.id_maestro} no encontrado"
            )
        id_maestro_asignado = maestro_asignado.id_maestro
    else:
        # Si no es admin, verificar roles
        person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
        roles = [pr.id_rol for pr in person_roles]
        
        es_pastor = 1 in roles
        es_maestro = 2 in roles
        
        if not es_pastor and not es_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para crear alumnos"
            )
        
        if es_pastor:
            # Pastor puede asignar a cualquier maestro
            if not alumno_data.id_maestro:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Los pastores deben proporcionar id_maestro para asignar el alumno"
                )
            
            # Verificar que el maestro existe
            maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == alumno_data.id_maestro).first()
            if not maestro_asignado:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Maestro con id {alumno_data.id_maestro} no encontrado"
                )
            id_maestro_asignado = maestro_asignado.id_maestro
        
        elif es_maestro:
            # Maestro se auto-asigna (ignora id_maestro del body)
            maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
            if not maestro:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Usuario no tiene registro de maestro en el sistema"
                )
            id_maestro_asignado = maestro.id_maestro
    
    # 5. Crear un nuevo auth_user_id para el alumno
    nuevo_auth_user_id = uuid.uuid4()
    
    # 6. Crear la persona del alumno
    nueva_persona = Persona(
        auth_user_id=nuevo_auth_user_id,
        nombre=alumno_data.nombre,
        apellido=alumno_data.apellido,
        email=alumno_data.email,
        foto_url=alumno_data.foto_url,
        id_perfil=3  # Perfil de usuario estándar
    )
    db.add(nueva_persona)
    db.flush()  # Para obtener el id_persona generado
    
    # 7. Crear el registro de alumno
    nuevo_alumno = Alumno(
        id_persona=nueva_persona.id_persona,
        dias=alumno_data.dias,
        franja_horaria=alumno_data.franja_horaria,
        motivo_oracion=alumno_data.motivo_oracion,
        id_estado_actual=alumno_data.id_estado_actual
    )
    db.add(nuevo_alumno)
    db.flush()  # Para obtener el id_alumno generado
    
    # 8. Crear la tarjeta de asignación
    nueva_tarjeta = Tarjeta(
        id_alumno=nuevo_alumno.id_alumno,
        id_maestro_asignado=id_maestro_asignado,
        id_estado_actual=1  # Estado "Activo" por defecto
    )
    db.add(nueva_tarjeta)
    
    # 9. Guardar todo en la base de datos
    try:
        db.commit()
        db.refresh(nueva_persona)
        db.refresh(nuevo_alumno)
        db.refresh(nueva_tarjeta)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el alumno: {str(e)}"
        )
    
    # 10. Obtener datos del maestro asignado para la respuesta
    maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == id_maestro_asignado).first()
    persona_maestro = None
    if maestro_asignado:
        persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_asignado.id_persona).first()
    
    # 11. Construir y retornar respuesta
    return {
        "message": "Alumno creado exitosamente",
        "alumno": {
            "id_alumno": str(nuevo_alumno.id_alumno),
            "id_tarjeta": str(nueva_tarjeta.id_tarjeta),
            "nombre": nueva_persona.nombre,
            "apellido": nueva_persona.apellido,
            "email": nueva_persona.email,
            "foto_url": nueva_persona.foto_url,
            "dias": nuevo_alumno.dias,
            "franja_horaria": nuevo_alumno.franja_horaria,
            "motivo_oracion": nuevo_alumno.motivo_oracion,
            "created_at": nuevo_alumno.created_at.isoformat() if nuevo_alumno.created_at else None,
            "maestro_asignado": {
                "id_maestro": str(maestro_asignado.id_maestro) if maestro_asignado else None,
                "nombre": persona_maestro.nombre if persona_maestro else None,
                "apellido": persona_maestro.apellido if persona_maestro else None,
                "telefono": maestro_asignado.telefono if maestro_asignado else None,
                "direccion": maestro_asignado.direccion if maestro_asignado else None
            } if maestro_asignado else None
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
            detail="No tienes permisos para acceder"
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
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
    nombre: Optional[str] = Form(None),
    apellido: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    franja_horaria: Optional[str] = Form(None),
    motivo_oracion: Optional[str] = Form(None),
    dias: Optional[str] = Form(None, description="JSON string con los días disponibles"),
    foto: Optional[UploadFile] = File(None)
):
    """
    Actualiza la información de un alumno específico.
    Acepta multipart/form-data. La foto se sube a Supabase Storage.
    El campo 'dias' debe enviarse como JSON string.
    Todos los campos son opcionales, solo se actualizan los que se envían.
    """
    
    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 2. Obtener perfil del usuario
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )
    
    es_admin = perfil.nivel_acceso == 1
    
    # 3. Buscar el alumno por ID
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alumno con id {id_alumno} no encontrado"
        )
    
    # 4. Obtener la tarjeta del alumno para verificar permisos
    tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == id_alumno).first()
    if not tarjeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información de asignación para este alumno"
        )
    
    # 5. Si no es admin, verificar permisos según roles
    if not es_admin:
        # Obtener roles del usuario autenticado
        person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
        roles = [pr.id_rol for pr in person_roles]
        
        # Verificar que tenga rol de pastor o maestro
        es_pastor = 1 in roles
        es_maestro = 2 in roles
        
        if not es_pastor and not es_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para actualizar alumnos"
            )
        
        # Si es maestro (y no pastor), verificar que el alumno le esté asignado
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
    
    # 6. Obtener la persona relacionada con el alumno
    persona_alumno = db.query(Persona).filter(Persona.id_persona == alumno.id_persona).first()
    if not persona_alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información personal del alumno"
        )
    
    # 7. Actualizar los campos de Persona (si se proporcionaron)
    if nombre is not None:
        persona_alumno.nombre = nombre
    if apellido is not None:
        persona_alumno.apellido = apellido
    if email is not None:
        persona_alumno.email = email

    # Subir foto a Supabase Storage si se proporcionó
    if foto and foto.filename:
        from app.integrations.storage import upload_foto
        persona_alumno.foto_url = upload_foto(foto, "alumnos")

    # 8. Actualizar los campos de Alumno (si se proporcionaron)
    if dias is not None:
        try:
            alumno.dias = json_lib.loads(dias)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El campo 'dias' debe ser un JSON válido"
            )
    if franja_horaria is not None:
        alumno.franja_horaria = franja_horaria
    if motivo_oracion is not None:
        alumno.motivo_oracion = motivo_oracion
    
    # 9. Guardar cambios en la base de datos
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
    
    # 10. Obtener datos del maestro asignado para la respuesta
    maestro_asignado = db.query(Maestro).filter(Maestro.id_maestro == tarjeta.id_maestro_asignado).first()
    persona_maestro = None
    if maestro_asignado:
        persona_maestro = db.query(Persona).filter(Persona.id_persona == maestro_asignado.id_persona).first()
    
    # 11. Construir y retornar respuesta
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


@router.delete("/{id_alumno}")
def delete_alumno(
    id_alumno: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Elimina un alumno y sus datos relacionados (tarjeta, observaciones).

    - Los administradores (nivel_acceso=1) pueden eliminar cualquier alumno.
    - Los pastores (id_rol=1) pueden eliminar cualquier alumno.
    - Los maestros (id_rol=2) solo pueden eliminar alumnos asignados a ellos.
    """

    # 1. Obtener la persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # 2. Obtener perfil del usuario
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )

    es_admin = perfil.nivel_acceso == 1

    # 3. Buscar alumno y tarjeta
    alumno = db.query(Alumno).filter(Alumno.id_alumno == id_alumno).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alumno con id {id_alumno} no encontrado"
        )

    tarjeta = db.query(Tarjeta).filter(Tarjeta.id_alumno == id_alumno).first()
    if not tarjeta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró información de asignación para este alumno"
        )

    # 4. Verificar permisos según el tipo de usuario
    if es_admin:
        # Los administradores pueden eliminar cualquier alumno sin restricciones
        pass
    else:
        # Si no es admin, verificar roles
        person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona_autenticada.id_persona).all()
        roles = [pr.id_rol for pr in person_roles]
        es_pastor = 1 in roles
        es_maestro = 2 in roles

        if not es_pastor and not es_maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para eliminar alumnos"
            )

        # Si es maestro (y no pastor), verificar que el alumno esté asignado a él
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
                    detail="No tienes permiso para eliminar este alumno"
                )

    # 5. Eliminar registros relacionados (tarjeta y alumno). Las FK con ON DELETE CASCADE
    # deberían encargarse de otras relaciones, pero borramos explícitamente para claridad.
    try:
        if tarjeta:
            db.delete(tarjeta)
        db.delete(alumno)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el alumno: {str(e)}"
        )

    return {"message": "Alumno eliminado correctamente", "id_alumno": str(id_alumno)}


@router.patch("/{id_alumno}/estado")
def cambiar_estado_alumno(
    id_alumno: str,
    estado_data: CambiarEstadoAlumno,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Cambia el estado de un alumno y registra el cambio en el historial.
    
    Permisos:
    - Administrador (nivel_acceso=1): Puede modificar cualquier alumno
    - Moderador/Maestro: Solo puede modificar alumnos asociados a él
    
    Args:
        id_alumno: UUID del alumno
        estado_data: Datos del nuevo estado y comentario opcional
        
    Returns:
        Confirmación del cambio con datos del historial creado
    """
    
    # 1. Validar UUID
    try:
        alumno_uuid = uuid.UUID(id_alumno)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de alumno inválido"
        )
    
    # 2. Obtener persona autenticada
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )
    
    # 3. Obtener perfil
    perfil = db.query(Profile).filter(Profile.id_perfil == persona_autenticada.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )
    
    es_admin = perfil.nivel_acceso == 1
    es_moderador = perfil.nivel_acceso == 2
    
    # 4. Verificar que el usuario sea admin o moderador
    if not (es_admin or es_moderador):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para cambiar estados de alumnos"
        )
    
    # 5. Verificar que el alumno existe
    alumno = db.query(Alumno).filter(Alumno.id_alumno == alumno_uuid).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alumno con id {id_alumno} no encontrado"
        )
    
    # 6. Si es moderador/maestro, verificar que el alumno esté asociado a él
    if not es_admin:
        # Obtener el maestro asociado al usuario autenticado
        maestro = db.query(Maestro).filter(Maestro.id_persona == persona_autenticada.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo maestros pueden modificar alumnos"
            )
        
        # Verificar que el alumno esté asociado al maestro
        tarjeta = db.query(Tarjeta).filter(
            Tarjeta.id_alumno == alumno.id_alumno,
            Tarjeta.id_maestro_asignado == maestro.id_maestro
        ).first()
        
        if not tarjeta:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para modificar este alumno"
            )
    
    # 7. Verificar que el estado existe
    estado = db.query(Estado).filter(Estado.id_estado == estado_data.id_estado).first()
    if not estado:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estado con id {estado_data.id_estado} no encontrado"
        )
    
    # 8. Verificar que el estado esté activo
    if not estado.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El estado '{estado.nombre}' no está activo"
        )
    
    # 9. Guardar el estado anterior
    estado_anterior = alumno.id_estado_actual
    
    # 10. Actualizar el estado del alumno
    alumno.id_estado_actual = estado_data.id_estado
    
    # 11. Crear registro en historial
    nuevo_historial = HistorialEstado(
        id_alumno=alumno.id_alumno,
        id_estado=estado_data.id_estado,
        comentario=estado_data.comentario,
        cambiado_por=persona_autenticada.id_persona
    )
    
    db.add(nuevo_historial)
    
    try:
        db.commit()
        db.refresh(alumno)
        db.refresh(nuevo_historial)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al cambiar el estado: {str(e)}"
        )
    
    # 12. Preparar respuesta
    return {
        "message": "Estado del alumno actualizado exitosamente",
        "id_alumno": str(alumno.id_alumno),
        "estado_anterior": estado_anterior,
        "estado_nuevo": estado_data.id_estado,
        "estado_nombre": estado.nombre,
        "historial": {
            "id_historial": str(nuevo_historial.id_historial),
            "fecha_cambio": nuevo_historial.fecha_cambio.isoformat(),
            "comentario": nuevo_historial.comentario,
            "cambiado_por": str(persona_autenticada.id_persona)
        }
    }


@router.get("/{id_alumno}/estados")
def get_estados_disponibles_alumno(
    id_alumno: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Devuelve los estados disponibles para un alumno, basado en la bolsa
    a la que pertenece su estado actual.

    Flujo: Alumno → id_estado_actual → Estado → id_bolsa → todos los estados de esa bolsa.

    Si el estado actual del alumno no pertenece a ninguna bolsa,
    se devuelve únicamente el estado actual.
    """

    # 1. Verificar usuario autenticado
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona no encontrada"
        )

    # 2. Obtener el alumno
    try:
        alumno_uuid = uuid.UUID(id_alumno)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="id_alumno no es un UUID válido"
        )

    alumno = db.query(Alumno).filter(Alumno.id_alumno == alumno_uuid).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alumno no encontrado"
        )

    if alumno.id_estado_actual is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El alumno no tiene un estado actual asignado"
        )

    # 3. Obtener el estado actual del alumno
    estado_actual = db.query(Estado).filter(Estado.id_estado == alumno.id_estado_actual).first()
    if not estado_actual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El estado actual del alumno no existe en la tabla de estados"
        )

    # 4. Si el estado pertenece a una bolsa, devolver todos los estados de esa bolsa
    if estado_actual.id_bolsa:
        bolsa = db.query(Bolsa).filter(Bolsa.id_bolsa == estado_actual.id_bolsa).first()

        estados = (
            db.query(Estado)
            .filter(Estado.id_bolsa == estado_actual.id_bolsa, Estado.activo == True)
            .order_by(Estado.orden)
            .all()
        )

        return {
            "id_alumno": str(alumno.id_alumno),
            "id_estado_actual": estado_actual.id_estado,
            "nombre_estado_actual": estado_actual.nombre,
            "bolsa": {
                "id_bolsa": str(bolsa.id_bolsa),
                "nombre": bolsa.nombre,
                "descripcion": bolsa.descripcion
            } if bolsa else None,
            "estados_disponibles": [
                {
                    "id_estado": e.id_estado,
                    "nombre": e.nombre,
                    "orden": e.orden,
                    "es_estado_actual": e.id_estado == estado_actual.id_estado
                }
                for e in estados
            ]
        }

    # 5. Si el estado no pertenece a ninguna bolsa, devolver solo el estado actual
    return {
        "id_alumno": str(alumno.id_alumno),
        "id_estado_actual": estado_actual.id_estado,
        "nombre_estado_actual": estado_actual.nombre,
        "bolsa": None,
        "estados_disponibles": [
            {
                "id_estado": estado_actual.id_estado,
                "nombre": estado_actual.nombre,
                "orden": estado_actual.orden,
                "es_estado_actual": True
            }
        ]
    }


@router.post("/{id_alumno}/observaciones", status_code=status.HTTP_201_CREATED)
def crear_observacion(
    id_alumno: str,
    body: ObservacionInput,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Agrega una observación al historial de un alumno.
    El autor queda registrado como la persona autenticada.

    Permisos:
    - Administrador (nivel_acceso=1): Puede agregar observaciones a cualquier alumno
    - Moderador (nivel_acceso=2): Solo puede agregar observaciones a alumnos asociados a él
    """
    # 1. Verificar que el alumno existe
    try:
        alumno_uuid = uuid.UUID(id_alumno)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de alumno inválido"
        )

    alumno = db.query(Alumno).filter(Alumno.id_alumno == alumno_uuid).first()
    if not alumno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alumno no encontrado"
        )

    # 2. Obtener la persona autenticada (autor)
    autor = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not autor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Autor no encontrado"
        )

    # 3. Verificar permisos: admin o moderador
    perfil = db.query(Profile).filter(Profile.id_perfil == autor.id_perfil).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil no encontrado"
        )

    es_admin = perfil.nivel_acceso == 1
    es_moderador = perfil.nivel_acceso == 2

    if not (es_admin or es_moderador):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para agregar observaciones a alumnos"
        )

    # 4. Si es moderador, verificar que el alumno esté asociado a él
    if not es_admin:
        maestro = db.query(Maestro).filter(Maestro.id_persona == autor.id_persona).first()
        if not maestro:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo maestros pueden agregar observaciones a alumnos"
            )

        tarjeta = db.query(Tarjeta).filter(
            Tarjeta.id_alumno == alumno.id_alumno,
            Tarjeta.id_maestro_asignado == maestro.id_maestro
        ).first()

        if not tarjeta:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para agregar observaciones a este alumno"
            )

    # 5. Crear la observación
    nueva_obs = Observacion(
        id_alumno=alumno_uuid,
        id_autor=autor.id_persona,
        texto=body.texto,
    )
    db.add(nueva_obs)
    db.commit()
    db.refresh(nueva_obs)

    return {
        "id_observacion": str(nueva_obs.id_observacion),
        "id_alumno": str(nueva_obs.id_alumno),
        "id_autor": str(nueva_obs.id_autor),
        "autor_nombre": autor.nombre,
        "autor_apellido": autor.apellido,
        "texto": nueva_obs.texto,
        "created_at": nueva_obs.created_at,
    }


# ---------------------------------------------------------------------------
# GET /{id_alumno}/historial  – cambios de estado del alumno
# ---------------------------------------------------------------------------

@router.get("/{id_alumno}/historial")
def get_historial_alumno(
    id_alumno: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve el historial de cambios de estado de un alumno, ordenado del más
    reciente al más antiguo.

    Cada entrada incluye:
    - Nombre del estado nuevo
    - Comentario (si existe)
    - Quién realizó el cambio (nombre + apellido)
    - Fecha del cambio
    """
    try:
        alumno_uuid = uuid.UUID(id_alumno)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de alumno inválido")

    # Verificar alumno
    alumno = db.query(Alumno).filter(Alumno.id_alumno == alumno_uuid).first()
    if not alumno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")

    # Verificar usuario autenticado
    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    # Obtener historial ordenado
    registros = (
        db.query(HistorialEstado)
        .filter(HistorialEstado.id_alumno == alumno_uuid)
        .order_by(HistorialEstado.fecha_cambio.desc())
        .all()
    )

    resultados = []
    for reg in registros:
        estado_obj = db.query(Estado).filter(Estado.id_estado == reg.id_estado).first()
        autor_obj = db.query(Persona).filter(Persona.id_persona == reg.cambiado_por).first() if reg.cambiado_por else None

        resultados.append({
            "id_historial": str(reg.id_historial),
            "id_estado": reg.id_estado,
            "estado_nombre": estado_obj.nombre if estado_obj else None,
            "comentario": reg.comentario,
            "fecha_cambio": reg.fecha_cambio.isoformat(),
            "cambiado_por": {
                "id_persona": str(autor_obj.id_persona) if autor_obj else None,
                "nombre": autor_obj.nombre if autor_obj else None,
                "apellido": autor_obj.apellido if autor_obj else None,
            },
        })

    return {
        "id_alumno": id_alumno,
        "total": len(resultados),
        "historial": resultados,
    }


# ---------------------------------------------------------------------------
# GET /{id_alumno}/observaciones  – comentarios del alumno
# ---------------------------------------------------------------------------

@router.get("/{id_alumno}/observaciones")
def get_observaciones_alumno(
    id_alumno: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve todas las observaciones/comentarios registrados para un alumno,
    ordenados del más reciente al más antiguo.

    Cada entrada incluye:
    - Texto del comentario
    - Quién lo escribió (nombre + apellido)
    - Fecha de creación
    """
    try:
        alumno_uuid = uuid.UUID(id_alumno)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de alumno inválido")

    alumno = db.query(Alumno).filter(Alumno.id_alumno == alumno_uuid).first()
    if not alumno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")

    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    registros = (
        db.query(Observacion)
        .filter(Observacion.id_alumno == alumno_uuid)
        .order_by(Observacion.created_at.desc())
        .all()
    )

    resultados = []
    for obs in registros:
        autor_obj = db.query(Persona).filter(Persona.id_persona == obs.id_autor).first()
        resultados.append({
            "id_observacion": str(obs.id_observacion),
            "texto": obs.texto,
            "created_at": obs.created_at.isoformat(),
            "autor": {
                "id_persona": str(autor_obj.id_persona) if autor_obj else None,
                "nombre": autor_obj.nombre if autor_obj else None,
                "apellido": autor_obj.apellido if autor_obj else None,
            },
        })

    return {
        "id_alumno": id_alumno,
        "total": len(resultados),
        "observaciones": resultados,
    }


# ---------------------------------------------------------------------------
# GET /{id_alumno}/actividad  – timeline unificado (estados + observaciones)
# ---------------------------------------------------------------------------

@router.get("/{id_alumno}/actividad")
def get_actividad_alumno(
    id_alumno: str,
    auth_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Devuelve un timeline unificado con todos los eventos del alumno mezclados
    y ordenados cronológicamente (más reciente primero).

    Cada evento tiene el campo 'tipo':
    - "cambio_estado": se cambió el estado del alumno
    - "observacion": un maestro o pastor dejó un comentario

    Ideal para mostrar en la página una única línea de tiempo de actividad.
    """
    try:
        alumno_uuid = uuid.UUID(id_alumno)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de alumno inválido")

    alumno = db.query(Alumno).filter(Alumno.id_alumno == alumno_uuid).first()
    if not alumno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alumno no encontrado")

    persona_autenticada = db.query(Persona).filter(Persona.auth_user_id == auth_user_id).first()
    if not persona_autenticada:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona no encontrada")

    eventos = []

    # --- Cambios de estado ---
    historial = (
        db.query(HistorialEstado)
        .filter(HistorialEstado.id_alumno == alumno_uuid)
        .all()
    )
    for reg in historial:
        estado_obj = db.query(Estado).filter(Estado.id_estado == reg.id_estado).first()
        autor_obj = db.query(Persona).filter(Persona.id_persona == reg.cambiado_por).first() if reg.cambiado_por else None
        eventos.append({
            "tipo": "cambio_estado",
            "fecha": reg.fecha_cambio,
            "id_referencia": str(reg.id_historial),
            "estado_nombre": estado_obj.nombre if estado_obj else None,
            "comentario": reg.comentario,
            "autor": {
                "id_persona": str(autor_obj.id_persona) if autor_obj else None,
                "nombre": autor_obj.nombre if autor_obj else None,
                "apellido": autor_obj.apellido if autor_obj else None,
            },
        })

    # --- Observaciones / comentarios ---
    observaciones = (
        db.query(Observacion)
        .filter(Observacion.id_alumno == alumno_uuid)
        .all()
    )
    for obs in observaciones:
        autor_obj = db.query(Persona).filter(Persona.id_persona == obs.id_autor).first()
        eventos.append({
            "tipo": "observacion",
            "fecha": obs.created_at,
            "id_referencia": str(obs.id_observacion),
            "texto": obs.texto,
            "autor": {
                "id_persona": str(autor_obj.id_persona) if autor_obj else None,
                "nombre": autor_obj.nombre if autor_obj else None,
                "apellido": autor_obj.apellido if autor_obj else None,
            },
        })

    # Ordenar por fecha descendente
    eventos.sort(key=lambda e: e["fecha"], reverse=True)

    # Serializar fechas
    for e in eventos:
        e["fecha"] = e["fecha"].isoformat()

    return {
        "id_alumno": id_alumno,
        "total": len(eventos),
        "actividad": eventos,
    }
