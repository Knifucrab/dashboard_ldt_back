from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class RegisterRequest(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str | None = None
    foto_url: str | None = None
    id_rol : int | None = None
    id_perfil : int | None = None

class RegisterMaestroRequest(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str
    foto_url: str | None = None
    telefono: str | None = None
    direccion: str | None = None

class RegisterAlumnoRequest(BaseModel):
    nombre: str
    apellido: str
    foto_url: str | None = None
    maestro_asignado: str  # id_persona del maestro
    dias: dict | None = None
    franja_horaria: str | None = None
    motivo_oracion: str | None = None
    
class UserResponse(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str | None
    avatar: str | None    
    
class LoginResponse(BaseModel):
    user: UserResponse
    token: str


class MaestroUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    email: EmailStr | None = None
    foto_url: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    password: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "Perez",
                "email": "juan.perez@example.com",
                "telefono": "555-1234",
                "direccion": "Calle 123",
            }
        }


class ChangeProfileRequest(BaseModel):
    id_perfil: int

    class Config:
        json_schema_extra = {
            "example": {
                "id_perfil": 1
            }
        }


class PersonaUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    email: EmailStr | None = None
    foto_url: str | None = None
    password: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan",
                "apellido": "Pérez",
                "email": "juan.perez@example.com",
                "foto_url": "https://example.com/foto.jpg"
            }
        }
