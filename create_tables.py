from app.database.base import Base
from app.database import engine

from app.models.role import Role
from app.models.profile import Profile
from app.models.persona import Persona
from app.models.maestro import Maestro
from app.models.alumno import Alumno
from app.models.estado import Estado
from app.models.tarjeta import Tarjeta
from app.models.historial_estado import HistorialEstado
from app.models.observacion import Observacion

def create_tables():
    Base.metadata.create_all(bind=engine)
    print("Tablas creadas correctamente")

if __name__ == "__main__":
    create_tables()