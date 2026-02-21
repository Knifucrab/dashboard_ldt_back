from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class HistorialEstadoBase(BaseModel):
    """Esquema base de HistorialEstado con campos comunes"""
    id_alumno: UUID
    id_estado: int
    comentario: str | None = None
    cambiado_por: UUID


class HistorialEstadoCreate(HistorialEstadoBase):
    """Esquema para crear un nuevo HistorialEstado"""
    pass


class HistorialEstadoUpdate(BaseModel):
    """Esquema para actualizar un HistorialEstado existente"""
    comentario: str | None = None


class HistorialEstadoResponse(HistorialEstadoBase):
    """Esquema de respuesta de HistorialEstado"""
    id_historial: UUID
    fecha_cambio: datetime

    class Config:
        from_attributes = True


class HistorialEstadoWithDetails(BaseModel):
    """Esquema de HistorialEstado con detalles completos"""
    id_historial: UUID
    id_alumno: UUID
    alumno_nombre: str
    alumno_apellido: str
    id_estado: int
    estado_descripcion: str
    fecha_cambio: datetime
    comentario: str | None = None
    cambiado_por: UUID
    cambiado_por_nombre: str
    cambiado_por_apellido: str

    class Config:
        from_attributes = True
