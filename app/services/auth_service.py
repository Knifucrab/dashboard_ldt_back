from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.persona import Persona
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.person_role import PersonRole
from app.core.security import create_access_token, hash_password, verify_password
from app.integrations.supabase_auth import supabase_login
from app.core.config import settings
import uuid
from app.models.role import Role
from app.models.profile import Profile
import traceback

def login_user(db: Session, email: str, password: str):
    # Autenticar con Supabase si está configurado
    supabase_user = supabase_login(email, password)
    
    if not supabase_user:
        # Si no hay Supabase, autenticar localmente con password hasheada
        if not (settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY):
            persona_local = db.query(Persona).filter(Persona.email == email).first()
            
            if not persona_local:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, 
                    detail="Credenciales inválidas"
                )
            
            # Validar la contraseña hasheada localmente
            if not persona_local.password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario no tiene contraseña configurada"
                )
            
            if not verify_password(password, persona_local.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
            
            # Autenticación local exitosa
            supabase_user = {"id": str(persona_local.auth_user_id)}
        else:
            # Supabase está configurado pero falló la autenticación
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Credenciales inválidas"
            )
    
    # Verificar si el usuario existe en la base de datos local
    persona = db.query(Persona).filter(Persona.auth_user_id == supabase_user["id"]).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Usuario no registrado en el sistema")
    
    # Obtener roles del usuario desde person_roles
    person_roles = db.query(PersonRole).filter(PersonRole.person_id == persona.id_persona).all()
    roles = [pr.id_rol for pr in person_roles]
    
    # Crear token JWT
    token = create_access_token(subject=persona.auth_user_id)
    
    return {
        "user": {
            "id": str(persona.id_persona),
            "email": persona.email,
            "name": f"{persona.nombre} {persona.apellido}",
            "role": str(roles[0]) if roles else None,
            "roles": [str(r) for r in roles],
            "avatar": persona.foto_url
        },
        "token": token
    }


def register_user(db: Session, nombre: str, apellido: str, email: str, password: str = None, foto_url: str = None, id_rol: int = None, id_perfil: int = None):
    # Create local Persona with given fields. Password is optional and will be hashed if provided.
    print(f"[debug] register_user called with nombre={nombre!r}, apellido={apellido!r}, email={email!r}, foto_url={foto_url!r}, id_rol={id_rol}, id_perfil={id_perfil}, password_provided={bool(password)}")

    # Validate and resolve role
    try:
        if id_rol is not None:
            role = db.query(Role).filter(Role.id_rol == id_rol).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El rol con id_rol={id_rol} no existe."
                )
        else:
            # Default: first available role
            role = db.query(Role).first()
            if not role:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No hay roles configurados en el sistema."
                )

        # Validate and resolve profile
        if id_perfil is not None:
            perfil = db.query(Profile).filter(Profile.id_perfil == id_perfil).first()
            if not perfil:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"El perfil con id_perfil={id_perfil} no existe."
                )
        else:
            # Default: first available profile
            perfil = db.query(Profile).first()
            if not perfil:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="No hay perfiles configurados en el sistema."
                )
    except HTTPException:
        raise
    except Exception as e:
        import sys
        print("[error] failed resolving role/profile:", file=sys.stderr)
        print(f"[error] Exception type: {type(e).__name__}", file=sys.stderr)
        print(f"[error] Exception message: {str(e)}", file=sys.stderr)
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error interno validando role/perfil: {type(e).__name__}")

    persona = Persona(
        auth_user_id=uuid.uuid4(),
        nombre=nombre or "",
        apellido=apellido or "",
        email=email,
        foto_url=foto_url,
        id_perfil=perfil.id_perfil,
    )

    # store hashed password locally if provided (optional, e.g., for non-supabase fallback)
    try:
        if password:
            persona.password = hash_password(password)
            print("[debug] password hashed and set on persona")

        db.add(persona)
        db.flush()  # Obtener id_persona sin hacer commit
        
        # Crear relación en person_roles
        person_role = PersonRole(
            person_id=persona.id_persona,
            id_rol=role.id_rol
        )
        db.add(person_role)
        
        print("[debug] persona added to session, committing...")
        db.commit()
        db.refresh(persona)
        print(f"[debug] persona committed with id_persona={persona.id_persona}")
    except IntegrityError as e:
        print("[error] integrity error creating persona:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya se encuentra registrado."
        )
    except Exception as e:
        print("[error] failed creating persona:")
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno registrando usuario")

    return {
        "id_persona": str(persona.id_persona),
        "email": persona.email,
        "name": f"{persona.nombre} {persona.apellido}",
    }


def register_maestro(
    db: Session,
    nombre: str,
    apellido: str,
    email: str,
    password: str,
    foto_url: str = None,
    telefono: str = None,
    direccion: str = None
):
    """Registra un nuevo maestro creando persona + maestro en una transacción"""
    print(f"[debug] register_maestro called for {email}")
    
    # Obtener rol de Maestro (id_rol=2)
    role_maestro = db.query(Role).filter(Role.id_rol == 2).first()
    if not role_maestro:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Rol 'Maestro' no configurado en el sistema"
        )
    
    # Obtener perfil de Maestro (id_perfil=2, siempre)
    perfil = db.query(Profile).filter(Profile.id_perfil == 2).first()
    if not perfil:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Perfil de Maestro (id_perfil=2) no configurado en el sistema"
        )
    
    try:
        # Crear persona
        persona = Persona(
            auth_user_id=uuid.uuid4(),
            nombre=nombre,
            apellido=apellido,
            email=email,
            password=hash_password(password),
            foto_url=foto_url,
            id_perfil=perfil.id_perfil
        )
        db.add(persona)
        db.flush()  # Obtener id_persona sin hacer commit
        
        # Asignar rol de Maestro en person_roles
        person_role = PersonRole(
            person_id=persona.id_persona,
            id_rol=role_maestro.id_rol
        )
        db.add(person_role)
        
        # Crear maestro
        maestro = Maestro(
            id_persona=persona.id_persona,
            telefono=telefono,
            direccion=direccion
        )
        db.add(maestro)
        db.commit()
        db.refresh(persona)
        db.refresh(maestro)
        
        print(f"[debug] maestro registered: persona={persona.id_persona}, maestro={maestro.id_maestro}")
        
        return {
            "id_persona": str(persona.id_persona),
            "id_maestro": str(maestro.id_maestro),
            "email": persona.email,
            "name": f"{persona.nombre} {persona.apellido}",
            "telefono": maestro.telefono,
            "direccion": maestro.direccion
        }
        
    except IntegrityError as e:
        db.rollback()
        print(f"[error] integrity error: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El email ya se encuentra registrado."
        )
    except Exception as e:
        db.rollback()
        print(f"[error] failed registering maestro: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno registrando maestro"
        )

