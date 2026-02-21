from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class MaestroBase(BaseModel):
    """Esquema base de Maestro con campos comunes"""
    telefono: str | None = None
    direccion: str | None = None


class MaestroCreate(MaestroBase):
    """Esquema para crear un nuevo Maestro"""
    id_persona: UUID


class MaestroUpdate(BaseModel):
    """Esquema para actualizar un Maestro existente"""
    telefono: str | None = None
    direccion: str | None = None


class MaestroResponse(MaestroBase):
    """Esquema de respuesta de Maestro"""
    id_maestro: UUID
    id_persona: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class MaestroWithPersona(MaestroResponse):
    """Esquema de Maestro con información de la persona"""
    nombre: str
    apellido: str
    email: str | None = None
    foto_url: str | None = None

    class Config:
        from_attributes = True
