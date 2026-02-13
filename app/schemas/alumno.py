from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any


class AlumnoUpdate(BaseModel):
    """Schema para actualizar información de un alumno"""
    # Datos de persona
    nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    apellido: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    foto_url: Optional[str] = None
    
    # Datos de alumno
    dias: Optional[Dict[str, Any]] = Field(None, description="Diccionario de días disponibles")
    franja_horaria: Optional[str] = Field(None, max_length=100)
    motivo_oracion: Optional[str] = Field(None, max_length=300)
    
    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan.perez@example.com",
                "foto_url": "https://example.com/foto.jpg",
                "dias": {"lunes": True, "miercoles": True, "viernes": True},
                "franja_horaria": "mañana",
                "motivo_oracion": "Por la salud de mi familia"
            }
        }
