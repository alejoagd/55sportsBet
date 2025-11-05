from __future__ import annotations
import typer
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from typing import Dict, Tuple, Optional
from config import settings


app = typer.Typer(help="Carga datos H2H.xlsx en Postgres (teams, matches, match_stats)")


# ===============================
# CONFIG
# ===============================
# Ajusta esto a tu conexión real. Ideal: lee de variables de entorno.
PG_DSN = settings.sqlalchemy_url

EXCEL_PATH_DEFAULT = "../data/H2H.xlsx"

LEAGUE_ID_DEFAULT = 1  # Premier League en tu tabla teams/seasons


# ===============================
# HELPERS
# ===============================

def get_engine() -> Engine:
    return create_engine(PG_DSN)


def normalize_team_name(name: str) -> str:
    """
    Limpieza básica para comparar equipos entre Excel y DB.
    Aquí puedes estandarizar tildes, 'Man United' vs 'Man Utd', etc.
    De momento solo strip().
    """
    if name is None:
        return ""
    return name.strip()


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
        if n < 100:          # 00..99 -> 2000..2099 (ajusta si necesitas 1990s)
            return 2000 + n
        return n

    start_year = to_year(a)
    end_year = to_year(b)
    # Ej: 24/25 -> 2024/2025; 12/13 -> 2012/2013
    return start_year, end_year



def load_reference_data(conn) -> Dict[str, Dict]:
    """
    Trae:
    - teams existentes (id por nombre normalizado)
    - seasons existentes (id por (year_start, year_end))
    """
    teams_rows = conn.execute(text("""
        SELECT id, name, league_id, status
        FROM public.teams
    """)).fetchall()

    seasons_rows = conn.execute(text("""
        SELECT id, league_id, year_start, year_end
        FROM public.seasons
    """)).fetchall()

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
    Si no existe, inserta en teams con status 'Disabled' y lo agrega al cache.
    """
    norm = normalize_team_name(team_name).lower()
    if norm in cache["teams_by_name"]:
        return cache["teams_by_name"][norm]["id"]

    # insertar nuevo
    insert_team_q = text("""
        INSERT INTO public.teams (name, league_id, status)
        VALUES (:name, :league_id, 'Disabled')
        RETURNING id;
    """)
    new_id = conn.execute(insert_team_q, {
        "name": team_name.strip(),
        "league_id": league_id
    }).scalar_one()

    cache["teams_by_name"][norm] = {
        "id": new_id,
        "name": team_name.strip(),
        "league_id": league_id,
        "status": "Disabled",
    }

    return new_id


def resolve_season_id(conn, cache, season_label: str) -> int:
    """
    Convierte '2012-2013' en el season.id correcto usando year_start/year_end.
    """
    start_year, end_year = parse_season_label(season_label)

    key = (start_year, end_year)
    seasons_by_years = cache["seasons_by_years"]
    if key not in seasons_by_years:
        raise ValueError(
            f"No encuentro season_id para {season_label} "
            f"(year_start={start_year}, year_end={end_year}) en public.seasons"
        )

    return seasons_by_years[key]["id"]


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
    Ajusta los nombres de columnas según tu Excel real.
    """
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
        "home_shots": row["home_shots"],
        "away_shots": row["away_shots"],
        "home_shots_on_target": row["home_shots_on_target"],
        "away_shots_on_target": row["away_shots_on_target"],
        "home_fouls": row["home_fouls"],
        "away_fouls": row["away_fouls"],
        "home_corners": row["home_corners"],
        "away_corners": row["away_corners"],
        "home_yellow_cards": row["home_yellow_cards"],
        "away_yellow_cards": row["away_yellow_cards"],
        "home_red_cards": row["home_red_cards"],
        "away_red_cards": row["away_red_cards"],
        "total_goals": int(row["home_goals"]) + int(row["away_goals"]),
        "total_corners": row["total_corners"],
        "total_shots": row["total_shots"],
        "total_shots_on_target": row["total_shots_on_target"],
        "total_fouls": row["total_fouls"],
        "total_cardshome": int(row["home_yellow_cards"]) + int(row["home_red_cards"]),
        "total_cardsaway": int(row["away_yellow_cards"]) + int(row["away_red_cards"]),
        "total_cards": row["total_cards"],
    })


# ===============================
# PIPELINE PRINCIPAL
# ===============================

@app.command()
def load(
    excel_path: str = typer.Option(EXCEL_PATH_DEFAULT, help="Ruta del archivo H2H.xlsx"),
    league_id: int = typer.Option(LEAGUE_ID_DEFAULT, help="league_id a usar para nuevos teams"),
    dry_run: bool = typer.Option(False, help="Si True, no hace commit")
):
    """
    Lee el Excel y hace inserts en teams / matches / match_stats.
    """

    # 1. leer excel
    df = pd.read_excel(excel_path)

    # =========== COLUMN MAPPING ===========
    # Ajusta estos nombres a tu Excel real:
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

        # stats:
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
        "total_corners": "Total Corners",
        "total_shots": "Total Shots",
        "total_shots_on_target": "Total Shots Target",
        "total_fouls": "Total Fouls",
        "total_cards": "Total Cards",
    }

    # Renombrar columnas del df a nombres internos estándar
    df = df.rename(columns={v: k for (k, v) in colmap.items()})

    engine = get_engine()

    with engine.begin() as conn:
        cache = load_reference_data(conn)
        inserted_matches = 0
        inserted_teams = 0
        inserted_stats = 0

        for idx, row in df.iterrows():
            # TEAM IDs (crea si no existe)
            home_team_id = ensure_team(conn, cache, row["home_team_name"], league_id)
            away_team_id = ensure_team(conn, cache, row["away_team_name"], league_id)

             # SEASON ID (desde season_label)
            season_id = resolve_season_id(conn, cache, row["season_label"])

            # INSERT MATCH
            match_id = insert_match(
                conn=conn,
                season_id=season_id,
                match_date=row["match_date"],
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                home_goals=int(row["home_goals"]),
                away_goals=int(row["away_goals"]),
                halftime_home_goals=int(row["halftime_home_goals"]),
                halftime_away_goals=int(row["halftime_away_goals"]),
                fulltime_result=str(row["fulltime_result"]).strip() if pd.notna(row["fulltime_result"]) else None,
                halftime_result=str(row["halftime_result"]).strip() if pd.notna(row["halftime_result"]) else None,
                referee=str(row["referee"]).strip() if pd.notna(row["referee"]) else None,
            )
            inserted_matches += 1

            # INSERT MATCH_STATS
            insert_match_stats(conn, match_id, row)
            inserted_stats += 1

        if dry_run:
            # si dry_run, forzamos rollback lanzando excepción controlada
            raise typer.Exit(code=99)

    typer.echo(f"OK ✅")
    typer.echo(f"Matches insertados: {inserted_matches}")
    typer.echo(f"Stats insertadas:   {inserted_stats}")
    typer.echo(f"Teams únicos en cache: {len(cache['teams_by_name'])}")


if __name__ == "__main__":
    app()
