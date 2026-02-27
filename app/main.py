from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.estados import router as estados_router
from app.routes.auth import router as auth_router
from app.routes.alumnos import router as alumnos_router
from app.routes.maestros import router as maestros_router
from app.routes.personas import router as personas_router
from app.routes.bolsas import router as bolsas_router
from app.routes.config import router as config_router
from app.routes.actividad import router as actividad_router
from app.routes.dashboard import router as dashboard_router
from app.database import engine
from sqlalchemy import text
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Verifica conexión a BD al iniciar.
    En Vercel serverless, esto puede no ejecutarse en cada invocación.
    """
    try:
        import os
        if os.getenv("DATABASE_URL"):
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("DB connection OK")
        else:
            print("DATABASE_URL not configured, skipping DB check")
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
    
    yield

app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
# Orígenes permitidos.  Para producción reemplaza la lista con los dominios
# de tu frontend real; evita "*" cuando allow_credentials=True.
#
# NOTAS:
#  - "http://localhost:5173" → desarrollo local (Vite / dev server)
#  - "https://dashboard-ldt-front.vercel.app" → producción
#  - allow_credentials=True es necesario si el frontend envía cookies/tokens
#    de sesión.  Si sólo usas cabeceras Authorization: Bearer, puedes
#    establecerlo en False para mayor compatibilidad.
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://dashboard-ldt-front.vercel.app",
    # TODO (producción): añadir aquí cualquier otro dominio de frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    # Listado explícito en lugar de "*" para evitar conflictos con
    # allow_credentials=True en versiones antiguas de Starlette.
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Accept",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers",
    ],
)

app.include_router(estados_router)
app.include_router(auth_router)
app.include_router(alumnos_router)
app.include_router(maestros_router)
app.include_router(personas_router)
app.include_router(bolsas_router)
app.include_router(config_router)
app.include_router(actividad_router)
app.include_router(dashboard_router)


@app.get("/help")
def help_endpoint():
    return {
        "status": "ok",
        "routes": ["/estados", "/auth", "/alumnos", "/help", "/docs"],
        "endpoints": {
            "/alumnos": {
                "GET": {
                    "description": "Obtiene alumnos según el rol del usuario autenticado",
                    "comportamiento": {
                        "pastor": "Si role === 'pastor' (id_rol=1): Sin maestroId devuelve TODOS los alumnos. Con maestroId filtra por ese maestro específico.",
                        "maestro": "Si role === 'maestro' (id_rol=2): Devuelve solo los alumnos asignados al maestro autenticado. El parámetro maestroId es ignorado."
                    },
                    "query_params": {
                        "maestroId": "(opcional, solo para pastores) ID de persona del maestro para filtrar alumnos."
                    },
                    "headers": {
                        "Authorization": "Bearer {token}"
                    }
                }
            }
        }
    }

