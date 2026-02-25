import uuid
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings


def upload_foto(file: UploadFile, carpeta: str) -> str:
    """
    Sube un archivo de imagen a Supabase Storage y devuelve la URL pública.

    Args:
        file: Archivo recibido desde el endpoint (UploadFile)
        carpeta: Subcarpeta dentro del bucket ("alumnos" o "maestros")

    Returns:
        URL pública del archivo subido
    """
    from app.integrations.supabase_client import supabase

    if supabase is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase Storage no está configurado. Verifica SUPABASE_URL y SUPABASE_SERVICE_ROLE_KEY en el .env"
        )

    # Validar que sea imagen
    MIME_PERMITIDOS = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    content_type = file.content_type or ""
    if content_type not in MIME_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de archivo no permitido: {content_type}. Se aceptan: jpeg, png, webp, gif"
        )

    # Generar nombre único para evitar colisiones
    extension = "jpg"
    if file.filename and "." in file.filename:
        extension = file.filename.rsplit(".", 1)[-1].lower()

    filename = f"{carpeta}/{uuid.uuid4()}.{extension}"
    bucket = settings.SUPABASE_STORAGE_BUCKET

    content = file.file.read()

    try:
        supabase.storage.from_(bucket).upload(
            path=filename,
            file=content,
            file_options={"content-type": content_type}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al subir imagen a Supabase Storage: {str(e)}"
        )

    url = supabase.storage.from_(bucket).get_public_url(filename)
    return url
