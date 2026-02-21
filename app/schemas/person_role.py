from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class PersonRoleBase(BaseModel):
    """Esquema base de PersonRole con campos comunes"""
    person_id: UUID
    id_rol: int


class PersonRoleCreate(PersonRoleBase):
    """Esquema para crear una nueva relación Persona-Rol"""
    pass


class PersonRoleUpdate(BaseModel):
    """Esquema para actualizar una relación Persona-Rol"""
    id_rol: int | None = None


class PersonRoleResponse(PersonRoleBase):
    """Esquema de respuesta de PersonRole"""
    assigned_at: datetime

    class Config:
        from_attributes = True


class PersonRoleWithDetails(BaseModel):
    """Esquema con detalles completos de la relación Persona-Rol"""
    person_id: UUID
    id_rol: int
    role_descripcion: str
    assigned_at: datetime

    class Config:
        from_attributes = True
