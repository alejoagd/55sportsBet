from __future__ import annotations
import typer
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Dict, Tuple, Optional
from datetime import datetime
import os
from dotenv import load_dotenv
import pathlib

# ✅ SOLUCIÓN: Usar ruta absoluta basada en la ubicación del script
SCRIPT_DIR = pathlib.Path(__file__).parent.absolute()
# Si el script está en src/, subir un nivel a la raíz
if SCRIPT_DIR.name == 'ingest' and SCRIPT_DIR.parent.name == 'src':
    PROJECT_ROOT = SCRIPT_DIR.parent.parent  # src/ingest/ -> raíz
elif SCRIPT_DIR.name == 'src':
    PROJECT_ROOT = SCRIPT_DIR.parent  # src/ -> raíz
else:
    PROJECT_ROOT = SCRIPT_DIR  # Ya estamos en la raíz

# Determinar qué .env usar
ENV_FILE = os.getenv('ENV_FILE', '.env')
ENV_PATH = PROJECT_ROOT / ENV_FILE

print("=" * 60)
print("🔍 VERIFICACIÓN DE ARCHIVOS - BUNDESLIGA")
print("=" * 60)
print(f"Directorio del script: {SCRIPT_DIR}")
print(f"Directorio del proyecto: {PROJECT_ROOT}")
print(f"Variable ENV_FILE: {ENV_FILE}")
print(f"Ruta completa: {ENV_PATH}")
print(f"¿Archivo existe? {ENV_PATH.exists()}")
print("=" * 60)
print()

if not ENV_PATH.exists():
    print(f"❌ ERROR: No se encontró {ENV_PATH}")
    print(f"❌ Verifica que el archivo exista en: {PROJECT_ROOT}")
    print()
    print("Archivos .env encontrados en el proyecto:")
    for env_file in PROJECT_ROOT.rglob('.env*'):
        print(f"  - {env_file}")
    exit(1)

# Cargar el .env correcto
load_dotenv(ENV_PATH)
print(f"✅ Archivo cargado: {ENV_PATH}")
print()

# ===============================
# LEER VARIABLES DE .ENV
# ===============================
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD') or os.getenv('DB_PASS')

# Validar variables
missing_vars = []
if not DB_HOST:
    missing_vars.append('DB_HOST')
if not DB_NAME:
    missing_vars.append('DB_NAME')
if not DB_USER:
    missing_vars.append('DB_USER')
if not DB_PASSWORD:
    missing_vars.append('DB_PASSWORD o DB_PASS')

if missing_vars:
    print("❌ ERROR: Variables de entorno faltantes:")
    for var in missing_vars:
        print(f"   • {var}")
    print()
    print(f"Verifica tu archivo: {ENV_PATH}")
    exit(1)

# Construir DSN
PG_DSN = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

app = typer.Typer()


# ===============================
# CONFIG - AJUSTA ESTAS RUTAS
# ===============================
EXCEL_PATH_DEFAULT = str(PROJECT_ROOT / "data" / "H2H_Bundesliga.xlsx") 

# ⬅️ IMPORTANTE: ID de Bundesliga en tu base de datos
# SELECT id, name FROM leagues WHERE name LIKE '%Bundesliga%';
LEAGUE_ID_BUNDESLIGA = 4  # ⬅️ AJUSTAR SEGÚN TU BASE DE DATOS

# Verificación de BD
print("=" * 60)
print("🔍 VERIFICACIÓN DE BASE DE DATOS")
print("=" * 60)
print(f"Host: {DB_HOST}")
print(f"Port: {DB_PORT}")
print(f"Database: {DB_NAME}")
print(f"User: {DB_USER}")
print(f"Liga: Bundesliga (ID: {LEAGUE_ID_BUNDESLIGA})")
print("=" * 60)
print()

# Advertencia si es localhost
if DB_HOST in ['localhost', '127.0.0.1', '::1']:
    print("⚠️  ¡ADVERTENCIA! Estás apuntando a LOCALHOST")
    print("⚠️  Para usar PRODUCCIÓN, ejecuta:")
    print()
    print("    PowerShell:")
    print("    $env:ENV_FILE='.env.production'; python src\\ingest\\ingest_h2h_bundesliga.py ingest")
    print()
    print("    CMD:")
    print("    set ENV_FILE=.env.production && python src\\ingest\\ingest_h2h_bundesliga.py ingest")
    print()
    print("    Linux/Mac:")
    print("    ENV_FILE=.env.production python src/ingest/ingest_h2h_bundesliga.py ingest")
    print()
    respuesta = input("¿Continuar con LOCALHOST de todos modos? (s/N): ")
    if respuesta.lower() != 's':
        print("❌ Operación cancelada")
        exit(0)
else:
    print("✅ Apuntando a BASE DE DATOS DE PRODUCCIÓN")
    print(f"✅ {DB_HOST}")
    print()
    respuesta = input("⚠️  ¿CONFIRMAS que quieres MODIFICAR LA BD DE PRODUCCIÓN? (s/N): ")
    if respuesta.lower() != 's':
        print("❌ Operación cancelada por seguridad")
        exit(0)

print()
print("🚀 Continuando con la carga de datos de BUNDESLIGA...")
print()


# ===============================
# HELPERS
# ===============================

def get_engine() -> Engine:
    return create_engine(PG_DSN)


def reset_sequences(conn):
    """Resetea las secuencias de ID para evitar conflictos."""
    try:
        conn.execute(text("""
            SELECT setval('seasons_id_seq', 
                COALESCE((SELECT MAX(id) FROM seasons), 0) + 1, 
                false
            );
        """))
        
        conn.execute(text("""
            SELECT setval('teams_id_seq', 
                COALESCE((SELECT MAX(id) FROM teams), 0) + 1, 
                false
            );
        """))
        
        conn.execute(text("""
            SELECT setval('matches_id_seq', 
                COALESCE((SELECT MAX(id) FROM matches), 0) + 1, 
                false
            );
        """))
        
        print("✅ Secuencias de ID sincronizadas")
        
    except Exception as e:
        print(f"⚠️  Advertencia al resetear secuencias: {e}")


def normalize_team_name(name: str) -> str:
    """Normalización de nombres de equipos de Bundesliga."""
    if name is None:
        return ""
    
    normalization_dict = {
        # Bayern y Dortmund
        "bayern munich": "Bayern Munich",
        "bayern": "Bayern Munich",
        "fc bayern": "Bayern Munich",
        
        "dortmund": "Borussia Dortmund",
        "borussia dortmund": "Borussia Dortmund",
        "bvb": "Borussia Dortmund",
        
        # Top teams
        "leverkusen": "Bayer Leverkusen",
        "bayer leverkusen": "Bayer Leverkusen",
        
        "rb leipzig": "RB Leipzig",
        "leipzig": "RB Leipzig",
        
        "ein frankfurt": "Eintracht Frankfurt",
        "eintracht frankfurt": "Eintracht Frankfurt",
        "frankfurt": "Eintracht Frankfurt",
        
        "m'gladbach": "Borussia M'gladbach",
        "mgladbach": "Borussia M'gladbach",
        
        "wolfsburg": "VfL Wolfsburg",
        "vfl wolfsburg": "VfL Wolfsburg",
        
        "freiburg": "SC Freiburg",
        "sc freiburg": "SC Freiburg",
        
        "hoffenheim": "TSG Hoffenheim",
        "tsg hoffenheim": "TSG Hoffenheim",
        
        "stuttgart": "VfB Stuttgart",
        "vfb stuttgart": "VfB Stuttgart",
        
        "union berlin": "Union Berlin",
        "fc union berlin": "Union Berlin",
        
        "werder bremen": "Werder Bremen",
        "bremen": "Werder Bremen",
        
        # Mid-lower table teams
        "mainz": "Mainz 05",
        "mainz 05": "Mainz 05",
        
        "fc koln": "FC Köln",
        "koln": "FC Köln",
        
        "augsburg": "FC Augsburg",
        "fc augsburg": "FC Augsburg",
        
        "bochum": "VfL Bochum",
        "vfl bochum": "VfL Bochum",
        
        "heidenheim": "FC Heidenheim",
        "fc heidenheim": "FC Heidenheim",
        
        "schalke 04": "Schalke 04",
        "schalke": "Schalke 04",
        
        "hertha": "Hertha Berlin",
        "hertha berlin": "Hertha Berlin",
        
        "hamburg": "Hamburger SV",
        "hamburger sv": "Hamburger SV",
        
        "hannover": "Hannover 96",
        "hannover 96": "Hannover 96",
        
        "nurnberg": "Nürnberg",
        "1. fc nurnberg": "Nürnberg",
        
        "darmstadt": "Darmstadt 98",
        "darmstadt 98": "Darmstadt 98",
        
        "paderborn": "SC Paderborn",
        "sc paderborn": "SC Paderborn",
        
        "fortuna dusseldorf": "Fortuna Düsseldorf",
        "dusseldorf": "Fortuna Düsseldorf",
        
        "greuther furth": "Greuther Fürth",
        "furth": "Greuther Fürth",
        
        "bielefeld": "Arminia Bielefeld",
        "arminia bielefeld": "Arminia Bielefeld",
        
        "braunschweig": "Eintracht Braunschweig",
        "eintracht braunschweig": "Eintracht Braunschweig",
        
        "ingolstadt": "FC Ingolstadt",
        "fc ingolstadt": "FC Ingolstadt",
    }
    
    name_lower = name.strip().lower()
    return normalization_dict.get(name_lower, name.strip())


def parse_season_label(season_label: str) -> Tuple[int, int]:
    """Parse season label to (year_start, year_end)."""
    s = season_label.strip().lower()
    if s.startswith("season "):
        s = s.replace("season ", "", 1).strip()
    s = s.replace("-", "/").replace("–", "/")
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if len(parts) != 2:
        raise ValueError(f"Formato inesperado de season_label: {season_label}")
    a, b = parts

    def to_year(x: str) -> int:
        n = int(x)
        if n < 100:
            return 2000 + n
        return n

    start_year = to_year(a)
    end_year = to_year(b)
    return start_year, end_year


def load_reference_data(conn, league_id: int) -> Dict[str, Dict]:
    """Carga teams y seasons existentes."""
    teams_rows = conn.execute(text("""
        SELECT id, name, league_id, status
        FROM public.teams
        WHERE league_id = :league_id
    """), {"league_id": league_id}).fetchall()

    seasons_rows = conn.execute(text("""
        SELECT id, league_id, year_start, year_end
        FROM public.seasons
        WHERE league_id = :league_id
    """), {"league_id": league_id}).fetchall()

    teams_map = {}
    for (tid, tname, lid, status) in teams_rows:
        norm_name = normalize_team_name(tname)
        teams_map[norm_name] = {
            "id": tid,
            "name": tname,
            "league_id": lid,
            "status": status
        }

    seasons_map = {}
    for (sid, lid, ys, ye) in seasons_rows:
        seasons_map[(ys, ye)] = sid

    return {
        "teams": teams_map,
        "seasons": seasons_map
    }


def ensure_team(conn, team_name: str, league_id: int, teams_map: Dict) -> int:
    """
    Asegura que el equipo existe, si no lo crea.
    Primero busca en la BD (por si ya existe pero no está en el cache).
    """
    norm_name = normalize_team_name(team_name)
    
    # Primero buscar en el cache
    if norm_name in teams_map:
        return teams_map[norm_name]["id"]
    
    # Buscar en la BD (puede existir pero no estar en el cache inicial)
    check_query = text("""
        SELECT id, name, league_id, status
        FROM public.teams
        WHERE league_id = :league_id
          AND LOWER(name) = LOWER(:name)
        LIMIT 1
    """)
    
    existing_team = conn.execute(check_query, {
        "league_id": league_id,
        "name": norm_name
    }).fetchone()
    
    if existing_team:
        tid, tname, lid, status = existing_team
        teams_map[norm_name] = {
            "id": tid,
            "name": tname,
            "league_id": lid,
            "status": status
        }
        return tid
    
    # Si no existe, crear nuevo equipo
    print(f"   ➕ Creando equipo: {norm_name}")
    
    insert_query = text("""
        INSERT INTO public.teams (name, league_id, status)
        VALUES (:name, :league_id, 'active')
        RETURNING id
    """)
    
    result = conn.execute(insert_query, {
        "name": norm_name,
        "league_id": league_id
    })
    
    new_id = result.scalar()
    teams_map[norm_name] = {
        "id": new_id,
        "name": norm_name,
        "league_id": league_id,
        "status": "active"
    }
    print(f"   ✅ Equipo creado: {norm_name} (ID={new_id})")
    return new_id


def ensure_season(conn, year_start: int, year_end: int, league_id: int, seasons_map: Dict) -> int:
    """
    Asegura que la temporada existe, si no la crea.
    Primero busca en la BD (por si ya existe pero no está en el cache).
    """
    key = (year_start, year_end)
    
    # Primero buscar en el cache
    if key in seasons_map:
        return seasons_map[key]
    
    # Buscar en la BD (puede existir pero no estar en el cache inicial)
    check_query = text("""
        SELECT id FROM public.seasons
        WHERE league_id = :league_id
          AND year_start = :year_start
          AND year_end = :year_end
        LIMIT 1
    """)
    
    existing_season = conn.execute(check_query, {
        "league_id": league_id,
        "year_start": year_start,
        "year_end": year_end
    }).scalar()
    
    if existing_season:
        print(f"   ℹ️  Temporada {year_start}/{year_end} ya existía (ID={existing_season})")
        seasons_map[key] = existing_season
        return existing_season
    
    # Si no existe, crear nueva temporada
    print(f"   ➕ Creando nueva temporada: {year_start}/{year_end}")
    
    # Fechas típicas de la liga
    start_date = f"{year_start}-08-16"  # Fecha típica inicio Bundesliga
    end_date = f"{year_end}-05-25"      # Fecha típica fin Bundesliga
    
    insert_query = text("""
        INSERT INTO public.seasons (league_id, year_start, year_end, start_date, end_date)
        VALUES (:league_id, :year_start, :year_end, :start_date, :end_date)
        RETURNING id
    """)
    
    result = conn.execute(insert_query, {
        "league_id": league_id,
        "year_start": year_start,
        "year_end": year_end,
        "start_date": start_date,
        "end_date": end_date
    })
    
    new_id = result.scalar()
    seasons_map[key] = new_id
    print(f"   ✅ Temporada creada: {year_start}/{year_end} (ID={new_id})")
    return new_id


def match_exists(conn, season_id: int, home_team_id: int, away_team_id: int, match_date) -> Optional[int]:
    """Verifica si el partido existe."""
    result = conn.execute(text("""
        SELECT id FROM public.matches
        WHERE season_id = :season_id
          AND home_team_id = :home_team_id
          AND away_team_id = :away_team_id
          AND date = :match_date
        LIMIT 1
    """), {
        "season_id": season_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "match_date": match_date
    }).scalar()
    return result


def insert_or_update_match(conn, row: dict, season_id: int, home_team_id: int, away_team_id: int) -> str:
    """Inserta o actualiza un partido. Retorna 'inserted' o 'updated'."""
    match_date = row['Date']
    
    existing_id = match_exists(conn, season_id, home_team_id, away_team_id, match_date)
    
    if existing_id:
        # Actualizar
        conn.execute(text("""
            UPDATE public.matches
            SET 
                home_goals = :home_goals,
                away_goals = :away_goals,
                fulltime_result = :fulltime_result,
                halftime_homegoal = :halftime_homegoal,
                halftime_awaygoal = :halftime_awaygoal,
                halftime_result = :halftime_result,
                referee = :referee
            WHERE id = :match_id
        """), {
            "match_id": existing_id,
            "home_goals": int(row['FTHG']),
            "away_goals": int(row['FTAG']),
            "fulltime_result": row['FTR'],
            "halftime_homegoal": int(row['HTHG']),
            "halftime_awaygoal": int(row['HTAG']),
            "halftime_result": row['HTR'],
            "referee": row.get('Referee')
        })
        
        # Actualizar match_stats
        conn.execute(text("""
            INSERT INTO public.match_stats (
                match_id, home_shots, away_shots,
                home_shots_on_target, away_shots_on_target,
                home_fouls, away_fouls,
                home_corners, away_corners,
                home_yellow_cards, away_yellow_cards,
                home_red_cards, away_red_cards,
                total_corners, total_shots, total_shots_on_target,
                total_fouls, total_cards
            ) VALUES (
                :match_id, :home_shots, :away_shots,
                :home_shots_on_target, :away_shots_on_target,
                :home_fouls, :away_fouls,
                :home_corners, :away_corners,
                :home_yellow_cards, :away_yellow_cards,
                :home_red_cards, :away_red_cards,
                :total_corners, :total_shots, :total_shots_on_target,
                :total_fouls, :total_cards
            )
            ON CONFLICT (match_id) DO UPDATE SET
                home_shots = EXCLUDED.home_shots,
                away_shots = EXCLUDED.away_shots,
                home_shots_on_target = EXCLUDED.home_shots_on_target,
                away_shots_on_target = EXCLUDED.away_shots_on_target,
                home_fouls = EXCLUDED.home_fouls,
                away_fouls = EXCLUDED.away_fouls,
                home_corners = EXCLUDED.home_corners,
                away_corners = EXCLUDED.away_corners,
                home_yellow_cards = EXCLUDED.home_yellow_cards,
                away_yellow_cards = EXCLUDED.away_yellow_cards,
                home_red_cards = EXCLUDED.home_red_cards,
                away_red_cards = EXCLUDED.away_red_cards,
                total_corners = EXCLUDED.total_corners,
                total_shots = EXCLUDED.total_shots,
                total_shots_on_target = EXCLUDED.total_shots_on_target,
                total_fouls = EXCLUDED.total_fouls,
                total_cards = EXCLUDED.total_cards
        """), {
            "match_id": existing_id,
            "home_shots": int(row.get('Home Shots', 0)),
            "away_shots": int(row.get('Away Shots', 0)),
            "home_shots_on_target": int(row.get('Home Shots Target', 0)),
            "away_shots_on_target": int(row.get('Away Shots Target', 0)),
            "home_fouls": int(row.get('Home Fouls', 0)),
            "away_fouls": int(row.get('Away Fouls', 0)),
            "home_corners": int(row.get('Home Corners', 0)),
            "away_corners": int(row.get('Away Corners', 0)),
            "home_yellow_cards": int(row.get('Home Yellow Cards', 0)),
            "away_yellow_cards": int(row.get('Away Yellow Cards', 0)),
            "home_red_cards": int(row.get('Home Red Cards', 0)),
            "away_red_cards": int(row.get('Away Red Cards', 0)),
            "total_corners": int(row.get('Total Corners', 0)),
            "total_shots": int(row.get('Total Shots', 0)),
            "total_shots_on_target": int(row.get('Total Shots Target', 0)),
            "total_fouls": int(row.get('Total Fouls', 0)),
            "total_cards": int(row.get('Total Cards', 0))
        })
        
        return 'updated'
    else:
        # Insertar match
        result = conn.execute(text("""
            INSERT INTO public.matches (
                season_id, date,
                home_team_id, away_team_id,
                home_goals, away_goals, fulltime_result,
                halftime_homegoal, halftime_awaygoal, halftime_result,
                referee
            ) VALUES (
                :season_id, :date,
                :home_team_id, :away_team_id,
                :home_goals, :away_goals, :fulltime_result,
                :halftime_homegoal, :halftime_awaygoal, :halftime_result,
                :referee
            )
            RETURNING id
        """), {
            "season_id": season_id,
            "date": match_date,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
            "home_goals": int(row['FTHG']),
            "away_goals": int(row['FTAG']),
            "fulltime_result": row['FTR'],
            "halftime_homegoal": int(row['HTHG']),
            "halftime_awaygoal": int(row['HTAG']),
            "halftime_result": row['HTR'],
            "referee": row.get('Referee')
        })
        
        match_id = result.scalar()
        
        # Insertar match_stats
        conn.execute(text("""
            INSERT INTO public.match_stats (
                match_id, home_shots, away_shots,
                home_shots_on_target, away_shots_on_target,
                home_fouls, away_fouls,
                home_corners, away_corners,
                home_yellow_cards, away_yellow_cards,
                home_red_cards, away_red_cards,
                total_corners, total_shots, total_shots_on_target,
                total_fouls, total_cards
            ) VALUES (
                :match_id, :home_shots, :away_shots,
                :home_shots_on_target, :away_shots_on_target,
                :home_fouls, :away_fouls,
                :home_corners, :away_corners,
                :home_yellow_cards, :away_yellow_cards,
                :home_red_cards, :away_red_cards,
                :total_corners, :total_shots, :total_shots_on_target,
                :total_fouls, :total_cards
            )
        """), {
            "match_id": match_id,
            "home_shots": int(row.get('Home Shots', 0)),
            "away_shots": int(row.get('Away Shots', 0)),
            "home_shots_on_target": int(row.get('Home Shots Target', 0)),
            "away_shots_on_target": int(row.get('Away Shots Target', 0)),
            "home_fouls": int(row.get('Home Fouls', 0)),
            "away_fouls": int(row.get('Away Fouls', 0)),
            "home_corners": int(row.get('Home Corners', 0)),
            "away_corners": int(row.get('Away Corners', 0)),
            "home_yellow_cards": int(row.get('Home Yellow Cards', 0)),
            "away_yellow_cards": int(row.get('Away Yellow Cards', 0)),
            "home_red_cards": int(row.get('Home Red Cards', 0)),
            "away_red_cards": int(row.get('Away Red Cards', 0)),
            "total_corners": int(row.get('Total Corners', 0)),
            "total_shots": int(row.get('Total Shots', 0)),
            "total_shots_on_target": int(row.get('Total Shots Target', 0)),
            "total_fouls": int(row.get('Total Fouls', 0)),
            "total_cards": int(row.get('Total Cards', 0))
        })
        
        return 'inserted'


@app.command()
def ingest(
    excel_path: str = typer.Option(EXCEL_PATH_DEFAULT, help="Ruta al Excel de Bundesliga"),
    league_id: int = typer.Option(LEAGUE_ID_BUNDESLIGA, help="ID de Bundesliga en la BD")
):
    """
    Carga histórico de partidos de Bundesliga desde Excel H2H_Bundesliga.xlsx
    """
    
    print("=" * 70)
    print("🇮🇹 INGESTA DE DATOS HISTÓRICOS - BUNDESLIGA (ALEMANIA)")
    print("=" * 70)
    print()
    
    if not os.path.exists(excel_path):
        print(f"❌ ERROR: No se encontró el archivo Excel: {excel_path}")
        print()
        print("Ubica el archivo H2H_Bundesliga.xlsx en la carpeta 'data' o especifica:")
        print("  python src\\ingest\\ingest_h2h_bundesliga.py ingest --excel-path C:\\ruta\\completa\\archivo.xlsx")
        return
    
    print(f"📂 Archivo Excel: {excel_path}")
    print(f"🏆 Liga: Bundesliga (ID={league_id})")
    print()
    
    try:
        df = pd.read_excel(excel_path)
        print(f"✅ Excel cargado: {len(df)} filas")
        print()
    except Exception as e:
        print(f"❌ ERROR al leer el Excel: {e}")
        return
    
    required_cols = ['Season', 'Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"❌ ERROR: Faltan columnas: {missing}")
        return
    
    engine = get_engine()
    
    # Cargar datos de referencia FUERA de la transacción principal
    with engine.connect() as conn:
        print("🔄 Sincronizando secuencias...")
        with conn.begin():
            reset_sequences(conn)
        print()
        
        print("📥 Cargando datos de referencia...")
        ref_data = load_reference_data(conn, league_id)
        teams_map = ref_data["teams"]
        seasons_map = ref_data["seasons"]
        print(f"   ✅ {len(teams_map)} equipos existentes")
        print(f"   ✅ {len(seasons_map)} temporadas existentes")
        print()
    
    print("🔄 Procesando partidos...")
    inserted_count = 0
    updated_count = 0
    error_count = 0
    
    # Procesar cada partido en su propia transacción
    for idx, row in df.iterrows():
        try:
            with engine.begin() as conn:
                season_label = str(row['Season']).strip()
                year_start, year_end = parse_season_label(season_label)
                season_id = ensure_season(conn, year_start, year_end, league_id, seasons_map)
                
                home_team_name = str(row['HomeTeam']).strip()
                away_team_name = str(row['AwayTeam']).strip()
                home_team_id = ensure_team(conn, home_team_name, league_id, teams_map)
                away_team_id = ensure_team(conn, away_team_name, league_id, teams_map)
                
                action = insert_or_update_match(conn, row, season_id, home_team_id, away_team_id)
                
                if action == 'inserted':
                    inserted_count += 1
                elif action == 'updated':
                    updated_count += 1
            
            if (idx + 1) % 100 == 0:
                print(f"   Procesados: {idx + 1}/{len(df)}")
                
        except Exception as e:
            error_count += 1
            date_str = row.get('Date', 'N/A')
            home = row.get('HomeTeam', 'N/A')
            away = row.get('AwayTeam', 'N/A')
            print(f"   ❌ Error fila {idx + 1}: {date_str} {home} vs {away}")
            print(f"      {str(e)}")
    
    print()
    print("=" * 70)
    print("📊 RESUMEN DE INGESTA")
    print("=" * 70)
    print(f"✅ Partidos insertados: {inserted_count}")
    print(f"🔄 Partidos actualizados: {updated_count}")
    print(f"❌ Errores: {error_count}")
    print(f"📦 Total procesado: {len(df)}")
    print()
    
    if error_count == 0:
        print("🎉 ¡Ingesta completada exitosamente!")
    else:
        print("⚠️  Ingesta completada con algunos errores")
    
    print()


if __name__ == "__main__":
    app()