from sqlalchemy.orm import Session
from app.models.estado import Estado

MAX_ESTADOS = 15

def crear_estado(db: Session, nombre: str, orden: int):
    cantidad = db.query(Estado).filter(Estado.activo == True).count()
    
    if cantidad >= MAX_ESTADOS:
        raise ValueError(f"No se pueden crear mas de {MAX_ESTADOS} estados activos.")
    
    nuevo_estado = Estado(nombre=nombre, orden=orden, activo=True)
    db.add(nuevo_estado)
    db.commit()
    db.refresh(nuevo_estado)
    
    return nuevo_estado