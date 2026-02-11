from fastapi import FastAPI
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
                    "description": "Obtiene alumnos asignados a un maestro",
                    "query_params": {
                        "maestroId": "(opcional) ID de persona del maestro. Si no se proporciona, retorna alumnos del maestro autenticado. Solo pastores pueden usar este parámetro para consultar otros maestros."
                    },
                    "headers": {
                        "Authorization": "Bearer {token}"
                    }
                }
            }
        }
    }

