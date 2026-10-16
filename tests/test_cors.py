"""
CORS: si el dominio del frontend no está permitido, el sitio abre pero no
carga datos. Se inspecciona la configuración del middleware en vez de usar
TestClient para no sumar httpx a requirements.txt ni tocar la BD.
"""
import pytest
from starlette.middleware.cors import CORSMiddleware

from src.api import app


def _allowed_origins() -> list[str]:
    mw = next(m for m in app.user_middleware if m.cls is CORSMiddleware)
    return list(mw.kwargs["allow_origins"])


@pytest.mark.parametrize("origin", [
    "https://55sports-stats.com",
    "https://www.55sports-stats.com",
    "https://55sports-bet-q25k.vercel.app",
    "http://localhost:5173",
])
def test_origen_permitido(origin):
    assert origin in _allowed_origins()


def test_no_hay_comodin():
    # allow_credentials=True con "*" abriría la API a cualquier sitio.
    assert "*" not in _allowed_origins()
