# 55sportsBet

Plataforma de datos y predicciones de fútbol. Un backend en Python (FastAPI + PostgreSQL) calcula predicciones con los modelos Poisson y Weinston, y un frontend en React las muestra.

- **Backend:** Python + FastAPI + SQLAlchemy + PostgreSQL (`src/`). Desplegado en Render.
- **Frontend:** React 19 + Vite + TypeScript + Tailwind (`frontend/`). Desplegado en Vercel.
- **Competencias:** Premier League, La Liga, Serie A, Bundesliga, Liga Betplay, Liga Argentina, Brasileirao, Libertadores, Sudamericana y Mundial 2026.

Para la arquitectura y las convenciones del código, ver [`CLAUDE.md`](CLAUDE.md).

## Requisitos

| Herramienta | Versión | macOS | Windows |
|---|---|---|---|
| Python | 3.11 o 3.12 (evitar 3.14: fallan dependencias como `scipy`) | `brew install python@3.12` | [python.org](https://www.python.org/downloads/) (marcar "Add to PATH") |
| PostgreSQL | 16 o superior | `brew install postgresql@16` | [postgresql.org](https://www.postgresql.org/download/windows/) |
| Node.js | 20 o superior | `brew install node` | [nodejs.org](https://nodejs.org/) |
| Git | cualquiera | `brew install git` | [git-scm.com](https://git-scm.com/) |

## 1. Clonar el repositorio

```bash
git clone https://github.com/alejoagd/55sportsBet.git
cd 55sportsBet
```

## 2. Entorno virtual de Python e instalación

**macOS (zsh/bash)**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Si PowerShell bloquea el script de activación, ejecutar una vez:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

Cuando el entorno está activo, el prompt muestra `(.venv)`. Hay que activarlo en cada terminal nueva.

## 3. Base de datos local

### 3.1 Arrancar PostgreSQL

**macOS**
```bash
brew services start postgresql@16
echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```
En Homebrew el usuario de Postgres es el mismo de tu Mac (`whoami`) y **no tiene contraseña**.

**Windows:** el instalador crea el servicio y el usuario `postgres` con la contraseña que elegiste. Verifica que el servicio esté activo en "Servicios" (`postgresql-x64-NN`). Si `psql` no se reconoce, agrega `C:\Program Files\PostgreSQL\<versión>\bin` al PATH.

### 3.2 Crear el archivo `.env`

Copiar la plantilla y editarla (el `.env` nunca se sube a git):

```bash
cp .env.example .env          # macOS
copy .env.example .env        # Windows (cmd/PowerShell)
```

Contenido para **macOS**:
```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ligas_europeas
DB_USER=tu_usuario_de_mac      # resultado de `whoami`
DB_PASS=                       # vacío
DB_SCHEMA=public
APIFOOTBALL_KEY=               # opcional, solo para api-sports.io
```

Contenido para **Windows**: igual, pero `DB_USER=postgres` y `DB_PASS=` con tu contraseña.

> **No definas `DATABASE_URL` en el `.env` local.** Si existe, `src/config.py` la usa en vez de `DB_USER`/`DB_PASS`, y la conexión apunta a otra base.

### 3.3 Crear la base y cargar los datos

Crear la base vacía:
```bash
createdb ligas_europeas
```
(En Windows, con el usuario `postgres`: `createdb -U postgres ligas_europeas`.)

Luego cargar los datos copiándolos desde producción (Render). Necesitas el archivo `.env.production` con la `DATABASE_URL` de la base de Render (se pide al mantenedor; no se versiona). Producción corre PostgreSQL 18, y `pg_dump` debe ser de versión igual o superior a la del servidor.

**macOS**
```bash
brew install postgresql@18          # solo para pg_dump/psql de la copia
set -a; . ./.env.production; set +a
/opt/homebrew/opt/postgresql@18/bin/pg_dump "$DATABASE_URL" --no-owner --no-privileges -f render_dump.sql
unset DATABASE_URL DB_HOST DB_USER DB_PASS DB_NAME
dropdb --force ligas_europeas && createdb ligas_europeas
/opt/homebrew/opt/postgresql@18/bin/psql -q ligas_europeas < render_dump.sql
```

**Windows (PowerShell)**
```powershell
# Instalar PostgreSQL 18 (o solo sus herramientas de cliente) y usar su pg_dump
$env:DATABASE_URL = (Get-Content .env.production | Select-String '^DATABASE_URL=').ToString().Split('=',2)[1]
& "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" $env:DATABASE_URL --no-owner --no-privileges -f render_dump.sql
Remove-Item Env:DATABASE_URL
dropdb -U postgres --force ligas_europeas; createdb -U postgres ligas_europeas
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -q -d ligas_europeas -f render_dump.sql
```

Notas:
- El único error esperado es `unrecognized configuration parameter "transaction_timeout"` si cargas en una versión anterior a la 18. Es inofensivo.
- La operación solo **lee** de producción.
- Borra `render_dump.sql` al terminar si no lo necesitas.
- **Backups viejos:** el antiguo `mi_backup.sql` (UTF-16, desactualizado) ya no está en el repo. Si recibes un `.sql` generado en Windows con `>` de PowerShell, conviértelo antes: `iconv -f UTF-16 -t UTF-8 x.sql | tr -d '\r' > x_utf8.sql`. Al generar dumps usa siempre `pg_dump ... -f archivo`.

Verificar:
```bash
psql ligas_europeas -c "select count(*), max(date) from matches"
```

## 4. Ejecutar el backend

Con el entorno virtual activo, desde la raíz del proyecto:

```bash
python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```

Debe mostrar `✅ [config.py] BD: localhost/ligas_europeas` y no avisos de `BD no disponible`.

- API: http://localhost:8000
- Documentación interactiva: http://localhost:8000/docs

## 5. Ejecutar el frontend

En **otra terminal**:

```bash
cd frontend
npm install        # solo la primera vez
npm run dev
```

Abrir http://localhost:5173/. El frontend lee el backend desde `VITE_API_URL` (por defecto `http://localhost:8000`). Para apuntar a otro backend, crear `frontend/.env.local` con `VITE_API_URL=https://...`.

Otros comandos del frontend: `npm run build` y `npm run lint`.

## 6. Pruebas

```bash
python -m pytest -q
```

Los tests de CI corren contra un Postgres desechable, nunca contra producción.

## 7. Pipeline de predicciones

Flujo típico de una jornada (con el entorno activo):

```bash
# Antes de los partidos: fixtures + reentrenar + predicciones + betting lines + best bets
python src/scripts/run_update_automated.py --mode complete --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env

# Después de los partidos: resultados + evaluación + validación de apuestas
python src/scripts/run_update_automated.py --mode finish --date-from YYYY-MM-DD --date-to YYYY-MM-DD --leagues all --env-file .env
```

Modos disponibles: `complete`, `finish`, `predict`, `retrain`, `best-bets`. También hay una CLI por pasos:

```bash
python -m src.predictions.cli fit --season-id 2
python -m src.predictions.cli upcoming --season-id 2 --from 2025-09-13 --to 2025-09-14
python -m src.predictions.cli evaluate --season-id 2 --from 2025-09-13 --to 2025-09-14
```

En producción, estos pasos los ejecutan los workflows de GitHub Actions (`.github/workflows/`).

## Diferencias macOS / Windows

| Tarea | macOS (zsh) | Windows (PowerShell) |
|---|---|---|
| Activar venv | `source .venv/bin/activate` | `.\.venv\Scripts\Activate.ps1` |
| Variable para un comando | `ENV_FILE=.env.production python x.py` | `$env:ENV_FILE=".env.production"; python x.py` |
| Separador de rutas | `src/archivo.py` | `src\archivo.py` |
| Copiar archivo | `cp a b` | `copy a b` |
| Scripts `.bat` (`update-local.bat`, etc.) | no aplican | se ejecutan directamente |
| Emojis en consola fallan (`UnicodeEncodeError`) | no suele ocurrir | `$env:PYTHONIOENCODING="utf-8"` |

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `role "postgres" does not exist` | En macOS no existe el rol `postgres`. Usa `DB_USER=$(whoami)` y quita `DATABASE_URL` del `.env`. |
| `command not found: pip` / `psql` | Venv no activo, o falta agregar Postgres al PATH. |
| `invalid byte sequence for encoding "UTF8": 0xff` | El `.sql` está en UTF-16 (viene de PowerShell). Conviértelo con `iconv`. |
| API responde 500 y faltan tablas | La base está desactualizada. Vuelve a copiar desde producción (paso 3.3). |
| `pg_dump: server version mismatch` | Usa un `pg_dump` de versión igual o superior a la del servidor (18). |
| El frontend dice "Failed to fetch" | El backend no está corriendo en el puerto 8000, o devuelve 500. Revisa la terminal de uvicorn. |
