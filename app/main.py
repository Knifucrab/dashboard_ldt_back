from fastapi import FastAPI
from app.routes.estados import router as estados_router
from app.routes.auth import router as auth_router
from app.database import engine
from sqlalchemy import text

app = FastAPI()

app.include_router(estados_router)
app.include_router(auth_router)


@app.get("/help")
def help_endpoint():
    return {
        "status": "ok",
        "routes": ["/estados", "/auth", "/help", "/docs"]
    }


@app.on_event("startup")
async def startup_event():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("DB connection OK")
    except Exception as e:
        print("Failed to connect:", e)