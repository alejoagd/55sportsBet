# src/config.py
from dataclasses import dataclass
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

env_file = os.getenv('ENV_FILE', '.env')
load_dotenv(env_file, override=True)

@dataclass
class Settings:
# Obtener DATABASE_URL de Render o usar configuración local
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:
        # Si existe DATABASE_URL (producción), parsearla
        from urllib.parse import urlparse
        url = urlparse(DATABASE_URL)
        
        DB_HOST: str = url.hostname
        DB_PORT: int = url.port if url.port else 5432  # ✅ Usar 5432 como default si es None
        DB_NAME: str = url.path[1:]  # Quitar el / inicial
        DB_USER: str = url.username
        DB_PASS: str = url.password
    else:
        # Si no existe DATABASE_URL (desarrollo local), usar variables individuales
        DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")
        DB_PORT: int = int(os.getenv("DB_PORT", 5432))
        DB_NAME: str = os.getenv("DB_NAME", "postgres")
        DB_USER: str = os.getenv("DB_USER", "postgres")
        DB_PASS: str = os.getenv("DB_PASS", "")

    @property
    def sqlalchemy_url(self) -> str:
        user = quote_plus(self.DB_USER)
        auth = f"{user}:{quote_plus(self.DB_PASS)}" if self.DB_PASS else user
        return f"postgresql+psycopg2://{auth}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# ⬇⬇⬇ ESTA LÍNEA ES CLAVE
settings = Settings()
