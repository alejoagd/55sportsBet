# src/db.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import settings

# 👇 ADAPTADORES PARA TIPOS NUMPY (evita el "schema np does not exist")
import numpy as np
from psycopg2.extensions import register_adapter, AsIs

def _adapt_np_float64(n): return AsIs(float(n))
def _adapt_np_float32(n): return AsIs(float(n))
def _adapt_np_int64(n):   return AsIs(int(n))
def _adapt_np_int32(n):   return AsIs(int(n))

register_adapter(np.float64, _adapt_np_float64)
register_adapter(np.float32, _adapt_np_float32)
register_adapter(np.int64,  _adapt_np_int64)
register_adapter(np.int32,  _adapt_np_int32)

engine = create_engine(settings.sqlalchemy_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def ping():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
