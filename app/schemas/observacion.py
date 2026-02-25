from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID


class ObservacionInput(BaseModel):
    """Esquema de entrada para crear una observación (solo requiere el texto)"""
    texto: str = Field(..., min_length=1, max_length=1000, description="Texto de la observación")

    class Config:
        json_schema_extra = {
            "example": {
                "texto": "El alumno mostró gran avance en la última semana."
            }
        }


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
