from supabase import create_client
from app.core.config import settings

# Create the supabase client only if the required settings exist.
supabase = None
if getattr(settings, "SUPABASE_URL", None) and getattr(settings, "SUPABASE_ANON_KEY", None):
    supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

def supabase_login(email: str, password: str):
    if supabase is None:
        return None
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response.user
    except Exception:
        return None