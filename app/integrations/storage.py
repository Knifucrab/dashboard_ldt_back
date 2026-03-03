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


def delete_foto(foto_url: str) -> None:
    """
    Elimina un archivo de Supabase Storage a partir de su URL pública.
    No lanza excepción si el archivo no existe o si Storage no está configurado.
    """
    from app.integrations.supabase_client import supabase

    print(f"[delete_foto] Iniciando. foto_url={foto_url!r}")

    if supabase is None:
        print("[delete_foto] Supabase client es None, abortando.")
        return
    if not foto_url:
        print("[delete_foto] foto_url está vacío o None, abortando.")
        return

    # Quitar query params que Supabase puede agregar (ej: ?t=1234567890)
    foto_url_clean = foto_url.split("?")[0]
    print(f"[delete_foto] foto_url limpia (sin query params)={foto_url_clean!r}")

    bucket = settings.SUPABASE_STORAGE_BUCKET
    print(f"[delete_foto] bucket configurado={bucket!r}")

    # Extraer el path sin depender del nombre exacto del bucket (evita problemas de casing)
    # URL pública: https://<project>.supabase.co/storage/v1/object/public/<bucket>/<path>
    base_marker = "/storage/v1/object/public/"
    idx = foto_url_clean.find(base_marker)
    if idx == -1:
        print(f"[delete_foto] No se encontró '{base_marker}' en la URL, abortando.")
        return

    after_marker = foto_url_clean[idx + len(base_marker):]
    print(f"[delete_foto] Segmento tras marker={after_marker!r}")

    # after_marker = "<bucket>/<path...>" — saltar el nombre del bucket
    slash_idx = after_marker.find("/")
    if slash_idx == -1:
        print("[delete_foto] No hay '/' tras el bucket en la URL, abortando.")
        return

    path = after_marker[slash_idx + 1:]
    print(f"[delete_foto] path a borrar={path!r}")

    if not path:
        print("[delete_foto] path vacío, abortando.")
        return

    try:
        result = supabase.storage.from_(bucket).remove([path])
        print(f"[delete_foto] Respuesta de Supabase Storage remove: {result}")
    except Exception as e:
        print(f"[delete_foto] Excepción al llamar a remove: {e}")

