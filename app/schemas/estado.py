from pydantic import BaseModel

class EstadoCreate(BaseModel):
    nombre: str
    orden: int
    
class EstadoUpdate(BaseModel):
    id_estado: int
    nombre: str | None = None
    orden: int | None = None
    activo: bool | None = None

class EstadoResponse(BaseModel):
    id_estado: int
    nombre: str
    orden: int
    activo: bool
    
    class Config:
        from_attributes = True