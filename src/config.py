# src/config.py
from dataclasses import dataclass
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

# Solo cargar .env si DATABASE_URL no está definido (desarrollo local)
if not os.getenv('DATABASE_URL'):
    env_file = os.getenv('ENV_FILE', '.env')
    load_dotenv(env_file, override=True)
    print(f"🔧 [config.py] Desarrollo - Cargando {env_file}")
else:
    print(f"🔧 [config.py] Producción - Usando DATABASE_URL del sistema")

@dataclass
class Settings:
    """Configuración de la base de datos"""
    
    def __post_init__(self):
        """Se ejecuta después de inicializar el dataclass"""
        # Obtener DATABASE_URL de Render o usar configuración local
        DATABASE_URL = os.getenv("DATABASE_URL")
        
        if DATABASE_URL:
            # Si existe DATABASE_URL (producción), parsearla
            from urllib.parse import urlparse
            url = urlparse(DATABASE_URL)
            
            self.DB_HOST = url.hostname
            self.DB_PORT = url.port if url.port else 5432
            self.DB_NAME = url.path[1:]  # Quitar el / inicial
            self.DB_USER = url.username
            self.DB_PASS = url.password
        else:
            # Si no existe DATABASE_URL (desarrollo local), usar variables individuales
            self.DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
            self.DB_PORT = int(os.getenv("DB_PORT", "5432"))
            self.DB_NAME = os.getenv("DB_NAME", "postgres")
            self.DB_USER = os.getenv("DB_USER", "postgres")
            # Support both DB_PASSWORD and DB_PASS
            self.DB_PASS = os.getenv("DB_PASSWORD") or os.getenv("DB_PASS", "")
    
    @property
    def sqlalchemy_url(self) -> str:
        user = quote_plus(self.DB_USER)
        auth = f"{user}:{quote_plus(self.DB_PASS)}" if self.DB_PASS else user
        return f"postgresql+psycopg2://{auth}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Esta línea es clave
settings = Settings()

# Verificar conexión
print(f"✅ [config.py] BD: {settings.DB_HOST}/{settings.DB_NAME}")