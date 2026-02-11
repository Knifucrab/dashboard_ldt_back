# Importar modelos en orden de dependencias
# Los modelos sin dependencias primero, luego los que dependen de ellos

from app.models.role import Role
from app.models.profile import Profile
from app.models.estado import Estado
from app.models.persona import Persona
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.observacion import Observacion
from app.models.tarjeta import Tarjeta
from app.models.historial_estado import HistorialEstado

__all__ = [
    "Role",
    "Profile",
    "Estado",
    "Persona",
    "Maestro",
    "Alumno",
    "Observacion",
    "Tarjeta",
    "HistorialEstado"
]
