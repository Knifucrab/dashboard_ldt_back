from pydantic import BaseModel
from datetime import datetime


class RoleBase(BaseModel):
    """Esquema base de Rol con campos comunes"""
    descripcion: str


class RoleCreate(RoleBase):
    """Esquema para crear un nuevo Rol"""
    id_rol: int


class RoleUpdate(BaseModel):
    """Esquema para actualizar un Rol existente"""
    descripcion: str | None = None


class RoleResponse(RoleBase):
    """Esquema de respuesta de Rol"""
    id_rol: int
    created_at: datetime

    class Config:
        from_attributes = True
