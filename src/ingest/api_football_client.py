# src/ingest/api_football_client.py
"""
Cliente para API-Football vía api-sports.io — SOLO para backfill histórico.

Verificado en vivo contra la key real del usuario (2026-07-24): el plan Free
da acceso a temporadas completas SOLO para season=2022/2023/2024. season=2025
y season=2026 (la actual), y el parámetro `next=`, están bloqueados en este
plan. Por eso este cliente se usa únicamente para cargar temporadas pasadas
que alimentan el entrenamiento de Poisson/Weinston — el calendario/resultados
de la temporada en curso se obtienen de ESPN (ver espn_competition_client.py).

Host/headers son los de api-sports.io directo (NO RapidAPI):
  base:   https://v3.football.api-sports.io
  header: x-apisports-key
"""
from __future__ import annotations
import json
import os
import time
from datetime import date
from pathlib import Path
import requests

BASE_URL = "https://v3.football.api-sports.io"
CACHE_DIR = Path("data/api_football_cache")
CALL_LOG = Path("logs/api_football_calls.log")

ALLOWED_HISTORICAL_SEASONS = (2022, 2023, 2024)


class APIFootballError(RuntimeError):
    pass


class APIFootballClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("APIFOOTBALL_KEY")
        if not self.api_key:
            raise APIFootballError("APIFOOTBALL_KEY no configurada (revisa .env/.env.production)")
        self.session = requests.Session()
        self.session.headers.update({"x-apisports-key": self.api_key})

    def _log_call(self, endpoint: str, params: dict) -> None:
        CALL_LOG.parent.mkdir(parents=True, exist_ok=True)
        with CALL_LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {endpoint} {params}\n")

    def _get(self, endpoint: str, params: dict, use_cache: bool = True) -> dict:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        key = "_".join(f"{k}-{v}" for k, v in sorted(params.items()))
        cache_file = CACHE_DIR / f"{endpoint}_{key}.json"

        if use_cache and cache_file.exists():
            return json.loads(cache_file.read_text(encoding="utf-8"))

        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                resp = self.session.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                last_exc = e
                print(f"   ⚠️  red inestable ({endpoint}, intento {attempt + 1}/4): {e}")
                time.sleep(2 * (attempt + 1))
        else:
            raise APIFootballError(f"No se pudo contactar {endpoint} tras varios intentos: {last_exc}")

        self._log_call(endpoint, params)

        errors = data.get("errors")
        if errors:
            raise APIFootballError(f"{endpoint} {params}: {errors}")

        cache_file.write_text(json.dumps(data), encoding="utf-8")
        time.sleep(0.3)
        return data

    def get_fixtures(self, league_id: int, season: int, use_cache: bool = True) -> list[dict]:
        """Fixtures completos de una temporada. Lanza APIFootballError si la temporada
        no está permitida en el plan actual (ver ALLOWED_HISTORICAL_SEASONS)."""
        data = self._get("fixtures", {"league": league_id, "season": season}, use_cache)
        return data.get("response", [])

    def get_standings(self, league_id: int, season: int, use_cache: bool = True) -> list[list[dict]]:
        """Retorna la lista de grupos (cada uno, lista de filas de standings) para
        temporadas con fase de grupos. Lista vacía si la competencia no tiene grupos."""
        data = self._get("standings", {"league": league_id, "season": season}, use_cache)
        resp = data.get("response", [])
        if not resp:
            return []
        return resp[0]["league"].get("standings", [])
