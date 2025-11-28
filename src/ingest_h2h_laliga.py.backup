from __future__ import annotations
import typer
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Dict, Tuple, Optional
from datetime import datetime
from config import settings

# No necesitamos config, usamos PG_DSN directamente
# from config import settings

app = typer.Typer()


# ===============================
# CONFIG - AJUSTA ESTAS RUTAS
# ===============================
# Conexión a PostgreSQL - ⚠️ IMPORTANTE: Ajusta con tus credenciales
PG_DSN = settings.sqlalchemy_url

EXCEL_PATH_DEFAULT = "../data/H2H_Laliga.xlsx"  # ⬅️ AJUSTAR RUTA

# ⬅️ IMPORTANTE: ID de La Liga en tu base de datos
# Según tu captura, league_id = 2 para La Liga
LEAGUE_ID_LA_LIGA = 2  # ⬅️ YA ESTÁ CORRECTO


# ===============================
# HELPERS
# ===============================

def get_engine() -> Engine:
    return create_engine(PG_DSN)


def reset_sequences(conn):
    """
    Resetea las secuencias de ID para evitar conflictos.
    Esto asegura que PostgreSQL use IDs disponibles.
    """
    try:
        # Resetear secuencia de seasons
        conn.execute(text("""
            SELECT setval('seasons_id_seq', 
                COALESCE((SELECT MAX(id) FROM seasons), 0) + 1, 
                false
            );
        """))
        
        # Resetear secuencia de teams
        conn.execute(text("""
            SELECT setval('teams_id_seq', 
                COALESCE((SELECT MAX(id) FROM teams), 0) + 1, 
                false
            );
        """))
        
        # Resetear secuencia de matches
        conn.execute(text("""
            SELECT setval('matches_id_seq', 
                COALESCE((SELECT MAX(id) FROM matches), 0) + 1, 
                false
            );
        """))
        
        print("✅ Secuencias de ID sincronizadas")
        
    except Exception as e:
        print(f"⚠️  Advertencia al resetear secuencias: {e}")
        print("   (Esto no debería afectar la carga)")


def normalize_team_name(name: str) -> str:
    """
    Limpieza básica para comparar equipos entre Excel y DB.
    Estandariza tildes, espacios, etc.
    """
    if name is None:
        return ""
    
    # Diccionario de normalización de nombres de equipos de La Liga
    normalization_dict = {
        "atletico madrid": "Atlético Madrid",
        "athletic bilbao": "Athletic Club",
        "athletic club": "Athletic Club",
        "real madrid": "Real Madrid",
        "fc barcelona": "Barcelona",
        "barcelona": "Barcelona",
        "real betis": "Real Betis",
        "betis": "Real Betis",
        "celta vigo": "Celta de Vigo",
        "celta": "Celta de Vigo",
        "sevilla": "Sevilla",
        "valencia": "Valencia",
        "villarreal": "Villarreal",
        "real sociedad": "Real Sociedad",
        "sociedad": "Real Sociedad",
        "espanyol": "Espanyol",
        "getafe": "Getafe",
        "levante": "Levante",
        "alaves": "Alavés",
        "deportivo alaves": "Alavés",
        "osasuna": "Osasuna",
        "ca osasuna": "Osasuna",
        "granada": "Granada",
        "mallorca": "Mallorca",
        "rcd mallorca": "Mallorca",
        "cadiz": "Cádiz",
        "elche": "Elche",
        "rayo vallecano": "Rayo Vallecano",
        "rayo": "Rayo Vallecano",
        "almeria": "Almería",
        "girona": "Girona",
        "valladolid": "Valladolid",
        "las palmas": "Las Palmas",
    }
    
    name_lower = name.strip().lower()
    return normalization_dict.get(name_lower, name.strip())


def parse_season_label(season_label: str) -> Tuple[int, int]:
    """
    Acepta 'Season 24/25', '24/25', '2012-2013', '12/13', etc.
    Devuelve (year_start, year_end) con años completos (2000+).
    """
    s = season_label.strip().lower()
    # quitar prefijo 'season '
    if s.startswith("season "):
        s = s.replace("season ", "", 1).strip()
    # normalizar separador
    s = s.replace("-", "/").replace("–", "/")
    parts = [p.strip() for p in s.split("/") if p.strip()]
    if len(parts) != 2:
        raise ValueError(f"Formato inesperado de season_label: {season_label}")
    a, b = parts

    def to_year(x: str) -> int:
        n = int(x)
        if n < 100:          # 00..99 -> 2000..2099
            return 2000 + n
        return n

    start_year = to_year(a)
    end_year = to_year(b)
    return start_year, end_year


def load_reference_data(conn, league_id: int) -> Dict[str, Dict]:
    """
    Trae:
    - teams existentes (id por nombre normalizado) de La Liga
    - seasons existentes (id por (year_start, year_end)) de La Liga
    """
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

    teams_by_name = {}
    for row in teams_rows:
        norm = normalize_team_name(row.name)
        teams_by_name[norm.lower()] = {
            "id": row.id,
            "name": row.name,
            "league_id": row.league_id,
            "status": row.status,
        }

    seasons_by_years = {}
    for row in seasons_rows:
        seasons_by_years[(row.year_start, row.year_end)] = {
            "id": row.id,
            "league_id": row.league_id,
            "year_start": row.year_start,
            "year_end": row.year_end,
        }

    return {
        "teams_by_name": teams_by_name,
        "seasons_by_years": seasons_by_years,
    }


def ensure_team(conn, cache, team_name: str, league_id: int) -> int:
    """
    Devuelve el team_id para team_name.
    Si no existe, inserta en teams con status 'Active' y lo agrega al cache.
    """
    normalized_name = normalize_team_name(team_name)
    norm_lower = normalized_name.lower()
    
    if norm_lower in cache["teams_by_name"]:
        return cache["teams_by_name"][norm_lower]["id"]

    # Verificar si ya existe en BD (por si el cache está desactualizado)
    check_team_q = text("""
        SELECT id FROM public.teams 
        WHERE LOWER(name) = LOWER(:name) 
          AND league_id = :league_id
    """)
    existing_team = conn.execute(check_team_q, {
        "name": normalized_name,
        "league_id": league_id
    }).scalar()
    
    if existing_team:
        print(f"  ℹ️  Equipo ya existía: {normalized_name} (id={existing_team})")
        cache["teams_by_name"][norm_lower] = {
            "id": existing_team,
            "name": normalized_name,
            "league_id": league_id,
            "status": "Active",
        }
        return existing_team

    # insertar nuevo equipo
    print(f"  ➕ Creando nuevo equipo: {normalized_name}")
    insert_team_q = text("""
        INSERT INTO public.teams (name, league_id, status)
        VALUES (:name, :league_id, 'Active')
        RETURNING id;
    """)
    new_id = conn.execute(insert_team_q, {
        "name": normalized_name,
        "league_id": league_id
    }).scalar_one()

    cache["teams_by_name"][norm_lower] = {
        "id": new_id,
        "name": normalized_name,
        "league_id": league_id,
        "status": "Active",
    }

    return new_id


def ensure_season(conn, cache, season_label: str, league_id: int) -> int:
    """
    Convierte '2012-2013' en el season.id correcto.
    Si no existe la temporada, la crea.
    """
    start_year, end_year = parse_season_label(season_label)

    key = (start_year, end_year)
    seasons_by_years = cache["seasons_by_years"]
    
    # Primero buscar en cache
    if key in seasons_by_years:
        season_data = seasons_by_years[key]
        # Verificar que sea de la liga correcta
        if season_data["league_id"] == league_id:
            return season_data["id"]
    
    # Buscar en BD si ya existe
    check_season_q = text("""
        SELECT id FROM public.seasons 
        WHERE league_id = :league_id 
          AND year_start = :year_start 
          AND year_end = :year_end
    """)
    existing_season = conn.execute(check_season_q, {
        "league_id": league_id,
        "year_start": start_year,
        "year_end": end_year
    }).scalar()
    
    if existing_season:
        print(f"  ℹ️  Temporada {start_year}/{end_year} ya existía (id={existing_season})")
        cache["seasons_by_years"][key] = {
            "id": existing_season,
            "league_id": league_id,
            "year_start": start_year,
            "year_end": end_year,
        }
        return existing_season
    
    # Crear nueva temporada
    print(f"  ➕ Creando nueva temporada: {start_year}/{end_year}")
    
    insert_season_q = text("""
        INSERT INTO public.seasons (league_id, year_start, year_end, start_date, end_date)
        VALUES (:league_id, :year_start, :year_end, :start_date, :end_date)
        RETURNING id;
    """)
    
    # Fechas típicas de La Liga
    start_date = f"{start_year}-08-16"
    end_date = f"{end_year}-05-25"
    
    new_season_id = conn.execute(insert_season_q, {
        "league_id": league_id,
        "year_start": start_year,
        "year_end": end_year,
        "start_date": start_date,
        "end_date": end_date
    }).scalar_one()
    
    cache["seasons_by_years"][key] = {
        "id": new_season_id,
        "league_id": league_id,
        "year_start": start_year,
        "year_end": end_year,
    }
    
    return new_season_id


def insert_match(
    conn,
    season_id: int,
    match_date,
    home_team_id: int,
    away_team_id: int,
    home_goals: int,
    away_goals: int,
    halftime_home_goals: int,
    halftime_away_goals: int,
    fulltime_result: str,
    halftime_result: str,
    referee: Optional[str],
) -> int:
    """
    Inserta en public.matches y retorna match_id (PK).
    """
    q = text("""
        INSERT INTO public.matches (
            season_id,
            date,
            home_team_id,
            away_team_id,
            home_goals,
            away_goals,
            fulltime_result,
            halftime_homegoal,
            halftime_awaygoal,
            halftime_result,
            referee
        )
        VALUES (
            :season_id,
            :date,
            :home_team_id,
            :away_team_id,
            :home_goals,
            :away_goals,
            :fulltime_result,
            :halftime_homegoal,
            :halftime_awaygoal,
            :halftime_result,
            :referee
        )
        RETURNING id;
    """)
    match_id = conn.execute(q, {
        "season_id": season_id,
        "date": match_date,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "fulltime_result": fulltime_result,
        "halftime_homegoal": halftime_home_goals,
        "halftime_awaygoal": halftime_away_goals,
        "halftime_result": halftime_result,
        "referee": referee,
    }).scalar_one()

    return match_id


def insert_match_stats(
    conn,
    match_id: int,
    row: pd.Series
):
    """
    Inserta las stats asociadas a ese partido en public.match_stats.
    """
    # Calcular totales
    home_cards = int(row.get("home_yellow_cards", 0)) + int(row.get("home_red_cards", 0))
    away_cards = int(row.get("away_yellow_cards", 0)) + int(row.get("away_red_cards", 0))
    total_cards = home_cards + away_cards
    
    q = text("""
        INSERT INTO public.match_stats (
            match_id,
            home_shots,
            away_shots,
            home_shots_on_target,
            away_shots_on_target,
            home_fouls,
            away_fouls,
            home_corners,
            away_corners,
            home_yellow_cards,
            away_yellow_cards,
            home_red_cards,
            away_red_cards,
            total_goals,
            total_corners,
            total_shots,
            total_shots_on_target,
            total_fouls,
            total_cardshome,
            total_cardsaway,
            total_cards
        )
        VALUES (
            :match_id,
            :home_shots,
            :away_shots,
            :home_shots_on_target,
            :away_shots_on_target,
            :home_fouls,
            :away_fouls,
            :home_corners,
            :away_corners,
            :home_yellow_cards,
            :away_yellow_cards,
            :home_red_cards,
            :away_red_cards,
            :total_goals,
            :total_corners,
            :total_shots,
            :total_shots_on_target,
            :total_fouls,
            :total_cardshome,
            :total_cardsaway,
            :total_cards
        );
    """)

    conn.execute(q, {
        "match_id": match_id,
        "home_shots": int(row.get("home_shots", 0)),
        "away_shots": int(row.get("away_shots", 0)),
        "home_shots_on_target": int(row.get("home_shots_on_target", 0)),
        "away_shots_on_target": int(row.get("away_shots_on_target", 0)),
        "home_fouls": int(row.get("home_fouls", 0)),
        "away_fouls": int(row.get("away_fouls", 0)),
        "home_corners": int(row.get("home_corners", 0)),
        "away_corners": int(row.get("away_corners", 0)),
        "home_yellow_cards": int(row.get("home_yellow_cards", 0)),
        "away_yellow_cards": int(row.get("away_yellow_cards", 0)),
        "home_red_cards": int(row.get("home_red_cards", 0)),
        "away_red_cards": int(row.get("away_red_cards", 0)),
        "total_goals": int(row.get("home_goals", 0)) + int(row.get("away_goals", 0)),
        "total_corners": int(row.get("total_corners", 0)),
        "total_shots": int(row.get("total_shots", 0)),
        "total_shots_on_target": int(row.get("total_shots_on_target", 0)),
        "total_fouls": int(row.get("total_fouls", 0)),
        "total_cardshome": home_cards,
        "total_cardsaway": away_cards,
        "total_cards": total_cards,
    })


# ===============================
# PIPELINE PRINCIPAL
# ===============================

@app.command("load")
def load_data(
    excel_path: str = typer.Option(EXCEL_PATH_DEFAULT, help="Ruta del archivo H2H_Laliga.xlsx"),
    league_id: int = typer.Option(LEAGUE_ID_LA_LIGA, help="league_id de La Liga"),
    dry_run: bool = typer.Option(False, help="Si True, no hace commit"),
    skip_rows: int = typer.Option(0, help="Filas a saltear al inicio del Excel")
):
    """
    Lee el Excel de La Liga y hace inserts en teams / seasons / matches / match_stats.
    """

    print(f"\n🔄 Iniciando carga de datos de La Liga...")
    print(f"📁 Archivo: {excel_path}")
    print(f"🏆 League ID: {league_id}")
    
    # 1. leer excel
    try:
        df = pd.read_excel(excel_path, skiprows=skip_rows)
        print(f"✅ Excel cargado: {len(df)} filas")
    except Exception as e:
        print(f"❌ Error al leer Excel: {e}")
        return

    # Mostrar las primeras columnas para verificar
    print(f"\n📋 Columnas encontradas:")
    for col in df.columns[:10]:
        print(f"   - {col}")
    
    # =========== COLUMN MAPPING ===========
    # ⬅️ IMPORTANTE: Ajusta estos nombres a las columnas EXACTAS de tu Excel
    colmap = {
        "match_date": "Date",
        "season_label": "Season",
        "home_team_name": "HomeTeam",
        "away_team_name": "AwayTeam",
        "home_goals": "FTHG",
        "away_goals": "FTAG",
        "halftime_home_goals": "HTHG",
        "halftime_away_goals": "HTAG",
        "fulltime_result": "FTR",
        "halftime_result": "HTR",
        "referee": "Referee",
        
        # Stats - ajusta según tu Excel
        "home_shots": "Home Shots",
        "away_shots": "Away Shots",
        "home_shots_on_target": "Home Shots Target",
        "away_shots_on_target": "Away Shots Target",
        "home_fouls": "Home Fouls",
        "away_fouls": "Away Fouls",
        "home_corners": "Home Corners",
        "away_corners": "Away Corners",
        "home_yellow_cards": "Home Yellow Cards",
        "away_yellow_cards": "Away Yellow Cards",
        "home_red_cards": "Home Red Cards",
        "away_red_cards": "Away Red Cards",
        
        # Si existen en tu Excel:
        "total_corners": "Total Corners",
        "total_shots": "Total Shots",
        "total_shots_on_target": "Total Shots Target",
        "total_fouls": "Total Fouls",
        "total_cards": "Total Cards",
    }

    # Renombrar solo las columnas que existan
    existing_colmap = {k: v for k, v in colmap.items() if v in df.columns}
    df = df.rename(columns={v: k for (k, v) in existing_colmap.items()})

    # Calcular totales si no existen
    if "total_corners" not in df.columns:
        df["total_corners"] = df.get("home_corners", 0) + df.get("away_corners", 0)
    if "total_shots" not in df.columns:
        df["total_shots"] = df.get("home_shots", 0) + df.get("away_shots", 0)
    if "total_shots_on_target" not in df.columns:
        df["total_shots_on_target"] = df.get("home_shots_on_target", 0) + df.get("away_shots_on_target", 0)
    if "total_fouls" not in df.columns:
        df["total_fouls"] = df.get("home_fouls", 0) + df.get("away_fouls", 0)

    engine = get_engine()

    try:
        with engine.begin() as conn:
            # ✅ Primero resetear las secuencias para evitar conflictos de ID
            reset_sequences(conn)
            
            print(f"\n🔄 Cargando datos de referencia...")
            cache = load_reference_data(conn, league_id)
            
            print(f"   - Equipos existentes: {len(cache['teams_by_name'])}")
            print(f"   - Temporadas existentes: {len(cache['seasons_by_years'])}")
            
            inserted_matches = 0
            inserted_teams = set()
            inserted_seasons = set()
            inserted_stats = 0
            errors = 0

            print(f"\n🔄 Procesando partidos...")
            for idx, row in df.iterrows():
                try:
                    # TEAM IDs (crea si no existe)
                    home_team_id = ensure_team(conn, cache, row["home_team_name"], league_id)
                    away_team_id = ensure_team(conn, cache, row["away_team_name"], league_id)
                    
                    inserted_teams.add(row["home_team_name"])
                    inserted_teams.add(row["away_team_name"])

                    # SEASON ID (crea si no existe)
                    season_id = ensure_season(conn, cache, row["season_label"], league_id)
                    inserted_seasons.add(row["season_label"])

                    # INSERT MATCH
                    match_id = insert_match(
                        conn=conn,
                        season_id=season_id,
                        match_date=row["match_date"],
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        home_goals=int(row.get("home_goals", 0)),
                        away_goals=int(row.get("away_goals", 0)),
                        halftime_home_goals=int(row.get("halftime_home_goals", 0)),
                        halftime_away_goals=int(row.get("halftime_away_goals", 0)),
                        fulltime_result=str(row.get("fulltime_result", "")).strip() if pd.notna(row.get("fulltime_result")) else None,
                        halftime_result=str(row.get("halftime_result", "")).strip() if pd.notna(row.get("halftime_result")) else None,
                        referee=str(row.get("referee", "")).strip() if pd.notna(row.get("referee")) else None,
                    )
                    inserted_matches += 1

                    # INSERT MATCH_STATS
                    insert_match_stats(conn, match_id, row)
                    inserted_stats += 1
                    
                    if inserted_matches % 100 == 0:
                        print(f"   ✓ Procesados {inserted_matches} partidos...")

                except Exception as e:
                    errors += 1
                    print(f"   ⚠️  Error en fila {idx}: {e}")
                    if errors > 10:
                        print(f"   ❌ Demasiados errores, abortando...")
                        raise

            if dry_run:
                print(f"\n🔄 DRY RUN - haciendo rollback...")
                raise typer.Exit(code=99)

    except typer.Exit:
        print(f"\n❌ Operación cancelada (DRY RUN)")
        return
    except Exception as e:
        print(f"\n❌ Error durante la carga: {e}")
        raise

    print(f"\n✅ CARGA COMPLETADA")
    print(f"═" * 50)
    print(f"📊 Resumen:")
    print(f"   - Partidos insertados: {inserted_matches}")
    print(f"   - Stats insertadas: {inserted_stats}")
    print(f"   - Equipos únicos: {len(inserted_teams)}")
    print(f"   - Temporadas únicas: {len(inserted_seasons)}")
    print(f"   - Equipos en cache: {len(cache['teams_by_name'])}")
    print(f"   - Errores: {errors}")
    print(f"═" * 50)


if __name__ == "__main__":
    app()