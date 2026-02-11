from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.persona import Persona
from app.core.security import create_access_token, hash_password
from app.integrations.supabase_auth import supabase_login
from app.core.config import settings
import uuid
from app.models.role import Role
from app.models.profile import Profile
import traceback

def login_user(db: Session, email: str, password: str):
    # Autenticar con Supabase
    supabase_user = supabase_login(email, password)
    # Si no hay cliente Supabase configurado, permitir un fallback de pruebas:
    # buscar por email en la base de datos local y considerar autenticado (sin verificar contraseña)
    if not supabase_user:
        if not (settings.SUPABASE_URL and settings.SUPABASE_ANON_KEY):
            persona_fallback = db.query(Persona).filter(Persona.email == email).first()
            if not persona_fallback:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
            supabase_user = {"id": str(persona_fallback.auth_user_id)}
        else:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales invalidas")
    
    # Verificar si el usuario existe en la base de datos local
    persona = (db.query(Persona).filter(Persona.auth_user_id == supabase_user["id"]).first())
    
    if not persona:
        raise HTTPException(status_code=404, detail="Usuario no registrado en el sistema")
    
    # Crear token JWT
    token = create_access_token(subject=persona.auth_user_id)
    
    return {
        "user": {
            "id": str(persona.id_persona),
            "email": persona.email,
            "name": f"{persona.nombre} {persona.apellido}",
            "role": str(persona.id_rol),
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
        print("[error] failed resolving role/profile:")
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error interno validando role/perfil")

    persona = Persona(
        auth_user_id=uuid.uuid4(),
        nombre=nombre or "",
        apellido=apellido or "",
        email=email,
        foto_url=foto_url,
        id_rol=role.id_rol,
        id_perfil=perfil.id_perfil,
    )

    # store hashed password locally if provided (optional, e.g., for non-supabase fallback)
    try:
        if password:
            persona.password = hash_password(password)
            print("[debug] password hashed and set on persona")

        db.add(persona)
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