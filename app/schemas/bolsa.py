from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class EstadoResponse(BaseModel):
    """Esquema de un estado dentro de una bolsa"""
    id_estado: int
    nombre: str
    orden: int
    activo: bool

    class Config:
        from_attributes = True


class BolsaBase(BaseModel):
    """Esquema base de Bolsa con campos comunes"""
    nombre: str
    descripcion: str | None = None
    activo: bool = True


class BolsaCreate(BolsaBase):
    """Esquema para crear una nueva Bolsa"""
    estados: list[str] = []


class BolsaUpdate(BaseModel):
    """Esquema para actualizar una Bolsa existente"""
    nombre: str | None = None
    descripcion: str | None = None
    estados: list[str] | None = None
    activo: bool | None = None


class BolsaResponse(BolsaBase):
    """Esquema de respuesta de Bolsa"""
    id_bolsa: UUID
    estados_orden: list[str] | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class BolsaWithEstados(BolsaResponse):
    """Esquema de Bolsa con lista completa de estados asociados"""
    total_estados: int
    estados_activos: int
    estados: list[EstadoResponse] = []

    class Config:
        from_attributes = True
