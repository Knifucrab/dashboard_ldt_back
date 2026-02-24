from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any


class AlumnoCreate(BaseModel):
    """Schema para crear un nuevo alumno"""
    # Datos de persona (requeridos)
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    foto_url: Optional[str] = None
    
    # Datos de alumno
    dias: Optional[Dict[str, Any]] = Field(None, description="Diccionario de días disponibles")
    franja_horaria: Optional[str] = Field(None, max_length=100)
    motivo_oracion: Optional[str] = Field(None, max_length=300)
    
    # Estado actual (obligatorio)
    id_estado_actual: int = Field(..., ge=1, description="ID del estado actual del alumno")
    
    # Maestro asignado (solo para admin, maestros se auto-asignan)
    id_maestro: Optional[str] = Field(None, description="ID del maestro a asignar (solo para administradores)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan.perez@example.com",
                "foto_url": "https://example.com/foto.jpg",
                "dias": {"lunes": True, "miercoles": True, "viernes": True},
                "franja_horaria": "mañana",
                "motivo_oracion": "Por la salud de mi familia",
                "id_estado_actual": 1,
                "id_maestro": "uuid-del-maestro"
            }
        }


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


class CambiarEstadoAlumno(BaseModel):
    """Schema para cambiar el estado de un alumno"""
    id_estado: int = Field(..., description="ID del nuevo estado")
    comentario: Optional[str] = Field(None, max_length=500, description="Comentario opcional sobre el cambio")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_estado": 3,
                "comentario": "El alumno completó el nivel básico"
            }
        }
