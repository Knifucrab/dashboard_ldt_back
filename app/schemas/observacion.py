from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ObservacionBase(BaseModel):
    """Esquema base de Observacion con campos comunes"""
    id_alumno: UUID
    id_autor: UUID
    texto: str


class ObservacionCreate(ObservacionBase):
    """Esquema para crear una nueva Observacion"""
    pass


class ObservacionUpdate(BaseModel):
    """Esquema para actualizar una Observacion existente"""
    texto: str | None = None


class ObservacionResponse(ObservacionBase):
    """Esquema de respuesta de Observacion"""
    id_observacion: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class ObservacionWithDetails(BaseModel):
    """Esquema de Observacion con detalles del alumno y autor"""
    id_observacion: UUID
    id_alumno: UUID
    alumno_nombre: str
    alumno_apellido: str
    id_autor: UUID
    autor_nombre: str
    autor_apellido: str
    texto: str
    created_at: datetime

    class Config:
        from_attributes = True
