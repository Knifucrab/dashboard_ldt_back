from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.estados import router as estados_router
from app.routes.auth import router as auth_router
from app.routes.alumnos import router as alumnos_router
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

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://dashboard-ldt-front.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(estados_router)
app.include_router(auth_router)
app.include_router(alumnos_router)


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

