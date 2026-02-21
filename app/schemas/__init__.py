from app.schemas.persona import (
    PersonaBase,
    PersonaCreate,
    PersonaUpdate,
    PersonaResponse,
    PersonaInDB
)
from app.schemas.profile import (
    ProfileBase,
    ProfileCreate,
    ProfileUpdate,
    ProfileResponse
)
from app.schemas.role import (
    RoleBase,
    RoleCreate,
    RoleUpdate,
    RoleResponse
)
from app.schemas.person_role import (
    PersonRoleBase,
    PersonRoleCreate,
    PersonRoleUpdate,
    PersonRoleResponse,
    PersonRoleWithDetails
)
from app.schemas.maestro import (
    MaestroBase,
    MaestroCreate,
    MaestroUpdate,
    MaestroResponse,
    MaestroWithPersona
)
from app.schemas.tarjeta import (
    TarjetaBase,
    TarjetaCreate,
    TarjetaUpdate,
    TarjetaResponse,
    TarjetaWithDetails
)
from app.schemas.historial_estado import (
    HistorialEstadoBase,
    HistorialEstadoCreate,
    HistorialEstadoUpdate,
    HistorialEstadoResponse,
    HistorialEstadoWithDetails
)
from app.schemas.observacion import (
    ObservacionBase,
    ObservacionCreate,
    ObservacionUpdate,
    ObservacionResponse,
    ObservacionWithDetails
)
from app.schemas.bolsa import (
    BolsaBase,
    BolsaCreate,
    BolsaUpdate,
    BolsaResponse,
    BolsaWithEstados
)
from app.schemas.alumno import *
from app.schemas.auth import *
from app.schemas.estado import *

__all__ = [
    # Persona schemas
    "PersonaBase",
    "PersonaCreate",
    "PersonaUpdate",
    "PersonaResponse",
    "PersonaInDB",
    # Profile schemas
    "ProfileBase",
    "ProfileCreate",
    "ProfileUpdate",
    "ProfileResponse",
    # Role schemas
    "RoleBase",
    "RoleCreate",
    "RoleUpdate",
    "RoleResponse",
    # PersonRole schemas
    "PersonRoleBase",
    "PersonRoleCreate",
    "PersonRoleUpdate",
    "PersonRoleResponse",
    "PersonRoleWithDetails",
    # Maestro schemas
    "MaestroBase",
    "MaestroCreate",
    "MaestroUpdate",
    "MaestroResponse",
    "MaestroWithPersona",
    # Tarjeta schemas
    "TarjetaBase",
    "TarjetaCreate",
    "TarjetaUpdate",
    "TarjetaResponse",
    "TarjetaWithDetails",
    # HistorialEstado schemas
    "HistorialEstadoBase",
    "HistorialEstadoCreate",
    "HistorialEstadoUpdate",
    "HistorialEstadoResponse",
    "HistorialEstadoWithDetails",
    # Observacion schemas
    "ObservacionBase",
    "ObservacionCreate",
    "ObservacionUpdate",
    "ObservacionResponse",
    "ObservacionWithDetails",
    # Bolsa schemas
    "BolsaBase",
    "BolsaCreate",
    "BolsaUpdate",
    "BolsaResponse",
    "BolsaWithEstados",
]
