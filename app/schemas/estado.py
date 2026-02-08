from pydantic import BaseModel

class EstadoCreate(BaseModel):
    nombre: str
    orden: int
    
class EstadoResponse(BaseModel):
    id_estado: int
    nombre: str
    orden: int
    activo: bool
    
    class Config:
        from_attributes = True