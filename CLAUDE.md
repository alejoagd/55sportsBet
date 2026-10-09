# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Stack real

- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2 (SQL crudo con `text()` casi siempre, no el ORM) + PostgreSQL. Desplegado en Render (`Procfile`: `uvicorn src.api:app`).
- **Frontend:** `frontend/` — React 19 + Vite + TypeScript + Tailwind 4, desplegado en Vercel. Lee el backend desde `VITE_API_URL` (por defecto `http://localhost:8000`).
- El `package.json` / `next.config.js` de la raíz son restos; el frontend real es `frontend/`.

## Comandos

```bash
# Backend (desde la raíz, con .venv activado)
pip install -r requirements.txt pytest
uvicorn src.api:app --reload             # API local en :8000
python -m pytest -q                      # todos los tests
python -m pytest tests/test_poisson.py::test_probs_sum_to_one   # un test

# Frontend
cd frontend && npm run dev               # :5173 (permitido en CORS)
cd frontend && npm run build             # tsc -b && vite build
cd frontend && npm run lint

# Pipeline de predicciones (lo mismo que corren los workflows)
python src/scripts/run_update_automated.py --mode {complete|finish|predict|retrain|best-bets} \
  --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env
python -m src.predictions.cli upcoming --season-id 76     # CLI typer (también: score, evaluate, fit, betting-lines, betting-lines-validate)
python -m src.scripts.run_predictions_for_competitions    # predicciones de las 5 competencias sudamericanas
```

En Windows, si un script imprime emojis y falla con `UnicodeEncodeError`, usar `PYTHONIOENCODING=utf-8`.

## Configuración y bases de datos

- `src/config.py` decide la conexión: si existe `DATABASE_URL` (Render) la usa; si no, carga `ENV_FILE` (por defecto `.env`) **con `override=True`**, que pisa cualquier variable de entorno ya definida. Acepta `DB_PASSWORD` o `DB_PASS`.
- `.env` = BD local (`localhost/ligas_europeas`); `.env.production` = BD de producción en Render. Ninguno se versiona (`.env.example` es la plantilla). Los workflows generan `.env.production` desde GitHub Secrets.
- La BD local se puede refrescar desde producción con `sync-local-from-prod.ps1` / `auto-sync-watcher.ps1`. Están en `.gitignore` porque llevan credenciales de producción, así que no vienen al clonar; hay que pedirlos al mantenedor.
- No hay herramienta de migraciones: hay SQL suelto en `migrations/` aplicado a mano, y `lifespan()` en `src/api.py` ejecuta `ALTER TABLE ... IF NOT EXISTS` al arrancar (con reintentos porque el DNS de Render falla transitoriamente).

## Arquitectura

**Flujo de datos:** ingesta (partidos/resultados/fixtures) → `matches` / `match_stats` → modelos (Poisson y Weinston) → `poisson_predictions` / `weinston_predictions` → betting lines → best bets → validación post-partido. La API solo lee y agrega estas tablas; el cálculo pesado se hace en scripts batch.

**Fuentes por competencia** (cada una tiene su propio camino de ingesta):
- 4 ligas europeas (códigos `E0`, `SP1`, `I1`, `D1`; ver `src/scripts/league_manager.py`): CSV de football-data.co.uk (`scripts/download-latest-data.py`), con respaldo de football-data.org (`sync_european_leagues_football_data.py`, que mapea equipos por id fijo en `TEAM_ID_MAP`, nunca por nombre, para no duplicar).
- 5 competencias sudamericanas (Brasileirao, Liga Argentina, Liga Betplay, Libertadores, Sudamericana) definidas en `src/ingest/competitions_config.py`: histórico desde API-Football (`load_api_football_history.py`, manual), temporada actual desde ESPN (`update_competitions_espn_sync.py`); Brasileirao además vía football-data.org.
- Mundial 2026 (`season_id` 76): scripts `update_wc2026_*.py` y `seed_wc2026_r32_schedule.py` en la raíz, con lógica de cuadro eliminatorio (placeholders de llave que luego se reconcilian con los equipos reales).
- Cada camino de ingesta es responsable de validar sus best bets al cargar resultados: el modo `finish` de `run_update_automated.py` solo cubre las ligas de `LeagueManager.LEAGUE_CSV_MAPPING` (europeas); los scripts sudamericanos llaman a `validate_pending_best_bets()` (`src/ingest/best_bets_validation.py`) en la misma transacción. Una fuente nueva que no lo haga deja best bets pendientes para siempre en `/best-bets`.
- `src/ingest/match_upsert.py` es el upsert compartido: busca por id externo de la fuente (`api_football_fixture_id`, `espn_event_id`) y si no, por `(season_id, home_id, away_id, date)` para no duplicar partidos.

**Modelos:** `src/poisson/` (probabilidades por goles esperados), `src/weinston/` (ratings ajustados con `fit`), `src/predictions/` (predicciones de próximos partidos, `league_context.py` con parámetros por liga, `h2h_scoring_system.py` para picks basados en historial H2H, evaluación y métricas).

**API:** `src/api.py` es un único archivo grande (~6000 líneas) con endpoints en `@app` y en un `router` incluido al final. Los modelos Pydantic de respuesta están definidos en el mismo archivo junto a cada endpoint.

**Automatización (GitHub Actions):**
- `update-predictions.yml`: dom/lun/mar = modo `finish` (resultados de los últimos 7 días + validación), miércoles = `complete` (fixtures + reentrenar + predicciones + betting lines + best bets).
- `update-api-football.yml`: 2 veces al día para las 5 competencias sudamericanas.
- `update-wc2026-results.yml`: 2 veces al día para el Mundial.
- `ci.yml`: pytest contra un Postgres de servicio desechable (nunca contra producción).

## Convenciones

- Nunca hacer commit directo a `main`; trabajar en ramas `fix/...` y abrir PR.
- Comentarios y mensajes de log en español; los comentarios explican el *porqué* (incidentes previos, decisiones), mantener ese estilo.
- Los endpoints no deben convertir datos faltantes en valores que parezcan reales (p. ej. `COALESCE(..., 0)`, promedios sobre muestras vacías). Para revisar endpoints nuevos o modificados de `src/api.py` existe el subagente `sql-safety-reviewer` (`.claude/agents/`).
- Los archivos `*.py.backup` son copias viejas; no editarlos.
