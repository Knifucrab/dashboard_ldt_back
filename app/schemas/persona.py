from pydantic import BaseModel, EmailStr
from datetime import datetime
from uuid import UUID


class PersonaBase(BaseModel):
    """Esquema base de Persona con campos comunes"""
    nombre: str
    apellido: str
    email: EmailStr | None = None
    foto_url: str | None = None
    id_perfil: int


class PersonaCreate(PersonaBase):
    """Esquema para crear una nueva Persona"""
    auth_user_id: UUID
    password: str | None = None


class PersonaUpdate(BaseModel):
    """Esquema para actualizar una Persona existente"""
    nombre: str | None = None
    apellido: str | None = None
    email: EmailStr | None = None
    foto_url: str | None = None
    id_perfil: int | None = None
    password: str | None = None


class PersonaResponse(PersonaBase):
    """Esquema de respuesta de Persona (sin password)"""
    id_persona: UUID
    auth_user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PersonaInDB(PersonaResponse):
    """Esquema completo de Persona incluyendo password"""
    password: str | None = None

    class Config:
        from_attributes = True
