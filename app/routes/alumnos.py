from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies.auth import get_current_user
from app.db.supabase import supabase
from fastapi import Query

router = APIRouter(prefix="/api/alumnos", tags=["Alumnos"])

@router.get("")
def get_alumnos(maestroId: str | None = Query(default=None), current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    user_id = current_user["id"]
    
    query = supabase.table("alumnos").select("""
        id,
        name,
        lastName,
        avatar,
        estado,
        maestroId,
        fechaIngreso,
        ultimaActividad,
        observaciones,
        diasDisponibles,
        franjaHoraria,
        motivoOracion,
        historial (
            id,
            fecha,
            descripcion,
            titulo,
            estadoNuevo,
            autor
        )
        """)
    
    # Reglas de acceso
    if role == "pastor":
        if maestroId:
            query = query.eq("maestroId", maestroId)
            
    elif role == "maestro":
        query = query.eq("maestroId", user_id)
        
    else:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    result = query.execute()
    
    if result.error:
        raise HTTPException(status_code=500, detail=result.error.message)
    
    return result.data