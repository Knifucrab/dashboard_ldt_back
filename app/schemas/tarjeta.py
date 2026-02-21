from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class TarjetaBase(BaseModel):
    """Esquema base de Tarjeta con campos comunes"""
    id_alumno: UUID
    id_estado_actual: int | None = None
    id_maestro_asignado: UUID | None = None


class TarjetaCreate(TarjetaBase):
    """Esquema para crear una nueva Tarjeta"""
    pass


class TarjetaUpdate(BaseModel):
    """Esquema para actualizar una Tarjeta existente"""
    id_estado_actual: int | None = None
    id_maestro_asignado: UUID | None = None


class TarjetaResponse(TarjetaBase):
    """Esquema de respuesta de Tarjeta"""
    id_tarjeta: UUID
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class TarjetaWithDetails(BaseModel):
    """Esquema de Tarjeta con detalles completos del alumno y maestro"""
    id_tarjeta: UUID
    id_alumno: UUID
    alumno_nombre: str
    alumno_apellido: str
    id_estado_actual: int | None = None
    estado_descripcion: str | None = None
    id_maestro_asignado: UUID | None = None
    maestro_nombre: str | None = None
    maestro_apellido: str | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
