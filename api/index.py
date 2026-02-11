import sys
from pathlib import Path

# Agregar el directorio raíz al path para que los imports funcionen
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.main import app

# Vercel serverless function handler
handler = app
