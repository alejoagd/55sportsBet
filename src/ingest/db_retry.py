# src/ingest/db_retry.py
"""Reintento simple para transacciones cuando el DNS/red del entorno es inestable."""
from __future__ import annotations
import time
from typing import Callable, TypeVar
from sqlalchemy.exc import OperationalError

T = TypeVar("T")


def run_with_retry(fn: Callable[[], T], attempts: int = 4, backoff_s: float = 2.0) -> T:
    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            return fn()
        except OperationalError as e:
            last_exc = e
            print(f"   ⚠️  BD inestable (intento {attempt + 1}/{attempts}): {e}")
            time.sleep(backoff_s * (attempt + 1))
    raise last_exc
