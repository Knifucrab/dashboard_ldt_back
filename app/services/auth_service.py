from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.persona import Persona
from app.core.security import create_access_token
from app.integrations.supabase_auth import supabase_login

def login_user(db: Session, email: str, password: str):
    # Autenticar con Supabase
    supabase_user = supabase_login(email, password)
    
    if not supabase_user:
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
            "role": persona.rol,
            "avatar": None
        },
        "token": token
    }