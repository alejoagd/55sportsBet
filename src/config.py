# src/config.py
from dataclasses import dataclass
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

load_dotenv()

@dataclass
class Settings:
    DB_HOST: str = os.getenv("DB_HOST", "127.0.0.1")   # mejor IPv4
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "postgres")
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASS: str = os.getenv("DB_PASS", "")            # puede estar vacío
    DB_SCHEMA: str = os.getenv("DB_SCHEMA", "public")

    @property
    def sqlalchemy_url(self) -> str:
        user = quote_plus(self.DB_USER)
        auth = f"{user}:{quote_plus(self.DB_PASS)}" if self.DB_PASS else user
        return f"postgresql+psycopg2://{auth}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# ⬇⬇⬇ ESTA LÍNEA ES CLAVE
settings = Settings()
