from pydantic import BaseModel
from datetime import datetime


class ProfileBase(BaseModel):
    """Esquema base de Perfil con campos comunes"""
    descripcion: str
    nivel_acceso: int


class ProfileCreate(ProfileBase):
    """Esquema para crear un nuevo Perfil"""
    id_perfil: int


class ProfileUpdate(BaseModel):
    """Esquema para actualizar un Perfil existente"""
    descripcion: str | None = None
    nivel_acceso: int | None = None


class ProfileResponse(ProfileBase):
    """Esquema de respuesta de Perfil"""
    id_perfil: int
    created_at: datetime

    class Config:
        from_attributes = True
