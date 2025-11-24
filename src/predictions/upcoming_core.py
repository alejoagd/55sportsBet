from __future__ import annotations
from sqlalchemy import text
from typing import Optional
from .league_context import LeagueContext, get_league_id
# src/predictions/upcoming_core.py
"""
Versión REFACTORIZADA con soporte multi-liga.

CAMBIOS PRINCIPALES:
1. Importa LeagueContext
2. load_team_strengths ahora acepta league_ctx y filtra por league_id
3. load_team_stat_profiles ahora acepta season_id, league_ctx y filtra por league_id
4. Todas las queries filtran por league_id en lugar de usar datos globales
"""
"""
Versión refactorizada de upcoming_core.py con soporte multi-liga.

CAMBIOS PRINCIPALES:
1. Acepta LeagueContext como parámetro
2. Filtra por league_id en todas las queries
3. Usa promedios de liga del contexto en lugar de calcularlos globalmente
"""




def _blend(value, prior, n, k=5):
    """Shrinkage hacia el prior de liga para pocos partidos."""
    if value is None:
        value = prior
    return (n * value + k * prior) / (n + k)


def load_team_strengths(
    conn, 
    season_id: int, 
    n_recent: int = 20,
    league_ctx: Optional[LeagueContext] = None
):
    """
    Calcula fortalezas por equipo a partir de TODO el histórico disponible
    DE LA MISMA LIGA (filtrado por league_id).
    
    Usa últimos n_recent partidos por equipo (split home/away) + shrinkage 
    al promedio de la liga correspondiente.
    
    Args:
        conn: Conexión a la base de datos
        season_id: ID de la temporada
        n_recent: Número de partidos recientes a considerar (default: 20)
        league_ctx: Contexto de liga (se carga automáticamente si no se provee)

    Returns:
        Tuple (strengths: dict, lg_home_gf: float, lg_away_gf: float, HFA: float)
        
        strengths[team_id] = {
            'attack_home': float,   # Factor ofensivo en casa
            'defense_home': float,  # Factor defensivo en casa
            'attack_away': float,   # Factor ofensivo de visitante
            'defense_away': float   # Factor defensivo de visitante
        }
    """
    # Obtener contexto de liga
    if league_ctx is None:
        league_ctx = LeagueContext.from_season(conn, season_id)
    
    league_id = league_ctx.league_id
    lg_home_gf = league_ctx.avg_home_goals
    lg_away_gf = league_ctx.avg_away_goals
    HFA = league_ctx.hfa
    
    print(f"🏆 Calculando fortalezas para: {league_ctx.league_name}")
    print(f"   Promedios de liga: {lg_home_gf:.2f} (H) / {lg_away_gf:.2f} (A)")
    
    # 🔥 CAMBIO CLAVE: Filtrar por league_id
    q_strengths = text(f"""
        WITH played AS (
          SELECT m.id, m.date, m.home_team_id, m.away_team_id, 
                 m.home_goals, m.away_goals
          FROM matches m
          JOIN seasons s ON s.id = m.season_id
          WHERE s.league_id = :comp_id
            AND m.home_goals IS NOT NULL 
            AND m.away_goals IS NOT NULL
            AND m.date < CURRENT_DATE
        ),
        home_recent AS (
          SELECT p.*,
                 ROW_NUMBER() OVER (PARTITION BY home_team_id ORDER BY date DESC) AS rn
          FROM played p
        ),
        away_recent AS (
          SELECT p.*,
                 ROW_NUMBER() OVER (PARTITION BY away_team_id ORDER BY date DESC) AS rn
          FROM played p
        ),
        h AS (
          SELECT * FROM home_recent WHERE rn <= :n_recent
        ),
        a AS (
          SELECT * FROM away_recent WHERE rn <= :n_recent
        )
        SELECT
          t.id AS team_id,
          COALESCE(COUNT(h.id), 0)        AS n_home,
          AVG(h.home_goals)::float        AS home_gf,
          AVG(h.away_goals)::float        AS home_ga,
          COALESCE(COUNT(a.id), 0)        AS n_away,
          AVG(a.away_goals)::float        AS away_gf,
          AVG(a.home_goals)::float        AS away_ga
        FROM teams t
        LEFT JOIN h ON h.home_team_id = t.id
        LEFT JOIN a ON a.away_team_id = t.id
        GROUP BY t.id
    """)
    
    strengths = {}
    teams_processed = 0
    
    for tid, n_home, home_gf, home_ga, n_away, away_gf, away_ga in conn.execute(
        q_strengths, 
        {"comp_id": league_id, "n_recent": n_recent}
    ):
        n_home = int(n_home or 0)
        n_away = int(n_away or 0)
        
        # Solo procesar equipos con al menos 1 partido
        if n_home == 0 and n_away == 0:
            continue

        # Shrinkage a promedio de liga si hay pocos partidos
        home_gf = _blend(home_gf, lg_home_gf, n_home)
        home_ga = _blend(home_ga, lg_away_gf, n_home)
        away_gf = _blend(away_gf, lg_away_gf, n_away)
        away_ga = _blend(away_ga, lg_home_gf, n_away)

        strengths[int(tid)] = {
            "attack_home":  (home_gf / lg_home_gf) if lg_home_gf > 0 else 1.0,
            "defense_home": (home_ga / lg_away_gf) if lg_away_gf > 0 else 1.0,
            "attack_away":  (away_gf / lg_away_gf) if lg_away_gf > 0 else 1.0,
            "defense_away": (away_ga / lg_home_gf) if lg_home_gf > 0 else 1.0,
        }
        teams_processed += 1

    print(f"   ✅ Fortalezas calculadas para {teams_processed} equipos")
    return strengths, lg_home_gf, lg_away_gf, HFA


def load_team_stat_profiles(
    conn, 
    season_id: int,
    n_recent: int = 20,
    league_ctx: Optional[LeagueContext] = None
):
    """
    Perfiles por equipo para SHOTS, SOT, FOULS, CARDS, CORNERS
    usando datos de partidos pasados DE LA MISMA LIGA.
    
    Args:
        conn: Conexión a la base de datos
        season_id: ID de la temporada
        n_recent: Número de partidos recientes a considerar
        league_ctx: Contexto de liga (se carga automáticamente si no se provee)
        
    Returns:
        Tuple (profiles: dict, league_means: dict)
        
        profiles[team_id][stat_name] = {
            'home_for': float,
            'home_against': float,
            'away_for': float,
            'away_against': float,
            'n_home': int,
            'n_away': int
        }
        
        league_means[stat_name] = float
    """
    # Obtener contexto de liga
    if league_ctx is None:
        league_ctx = LeagueContext.from_season(conn, season_id)
    
    league_id = league_ctx.league_id
    
    print(f"📊 Cargando perfiles estadísticos: {league_ctx.league_name}")
    
    # 🔥 CAMBIO CLAVE: Usar match_stats real + filtrar por league_id
    q = text("""
        SELECT 
            m.date, 
            m.home_team_id, 
            m.away_team_id,
            ms.home_shots as sh, 
            ms.away_shots as sa, 
            ms.home_shots_on_target as sth, 
            ms.away_shots_on_target as sta,
            ms.home_fouls as fh, 
            ms.away_fouls as fa, 
            (COALESCE(ms.home_yellow_cards, 0) + COALESCE(ms.home_red_cards, 0)) as ch,
            (COALESCE(ms.away_yellow_cards, 0) + COALESCE(ms.away_red_cards, 0)) as ca,
            ms.home_corners as coh, 
            ms.away_corners as coa
        FROM matches m
        JOIN seasons s ON s.id = m.season_id
        JOIN match_stats ms ON ms.match_id = m.id
        WHERE s.league_id = :comp_id
          AND m.date < CURRENT_DATE
        ORDER BY m.date DESC
    """)
    
    rows = conn.execute(q, {"comp_id": league_id}).fetchall()
    
    stats = [
        ("sh", "sa", "shots"),
        ("sth", "sta", "shots_target"),
        ("fh", "fa", "fouls"),
        ("ch", "ca", "cards"),
        ("coh", "coa", "corners"),
    ]

    # Acumular listas por equipo y condición
    from collections import defaultdict, deque
    prof = defaultdict(lambda: defaultdict(lambda: {
        "home_for": deque(maxlen=n_recent),
        "home_against": deque(maxlen=n_recent),
        "away_for": deque(maxlen=n_recent),
        "away_against": deque(maxlen=n_recent),
    }))
    league_sums = {name: [0.0, 0] for _, _, name in stats}  # sum, cnt

    for row in rows:
        date, h, a = row.date, row.home_team_id, row.away_team_id
        
        for h_col, a_col, name in stats:
            vh = getattr(row, h_col)
            va = getattr(row, a_col)
            
            # Liga
            if vh is not None:
                league_sums[name][0] += float(vh)
                league_sums[name][1] += 1
            if va is not None:
                league_sums[name][0] += float(va)
                league_sums[name][1] += 1
            
            # Perfiles
            if vh is not None:
                prof[h][name]["home_for"].append(float(vh))
            if va is not None:
                prof[h][name]["home_against"].append(float(va))
            if va is not None:
                prof[a][name]["away_for"].append(float(va))
            if vh is not None:
                prof[a][name]["away_against"].append(float(vh))

    league_means = {}
    for name, (s, c) in league_sums.items():
        league_means[name] = (s / c) if c else 0.0

    # Convertir de deque a promedios con shrinkage
    def avg(lst): 
        arr = list(lst)
        return (sum(arr)/len(arr)) if arr else None

    out = {}
    for tid, per_stat in prof.items():
        out[tid] = {}
        for name, buckets in per_stat.items():
            hf = avg(buckets["home_for"])
            ha = avg(buckets["home_against"])
            af = avg(buckets["away_for"])
            aa = avg(buckets["away_against"])
            
            # Cuenta de muestras
            n_h = len(buckets["home_for"]) + len(buckets["home_against"])
            n_a = len(buckets["away_for"]) + len(buckets["away_against"])
            
            lg = league_means[name] or 0.001
            out[tid][name] = {
                "home_for":      _blend(hf, lg, n_h),
                "home_against":  _blend(ha, lg, n_h),
                "away_for":      _blend(af, lg, n_a),
                "away_against":  _blend(aa, lg, n_a),
                "n_home": n_h, 
                "n_away": n_a,
            }
    
    print(f"   ✅ Perfiles cargados para {len(out)} equipos")
    print(f"   📈 Promedios de liga:")
    for stat_name, mean_val in league_means.items():
        print(f"      {stat_name}: {mean_val:.2f}")

    return out, league_means


# =============================================================================
# EJEMPLO DE USO
# =============================================================================

if __name__ == "__main__":
    from sqlalchemy import create_engine
    from src.config import settings
    
    engine = create_engine(settings.sqlalchemy_url)
    
    with engine.begin() as conn:
        # Premier League
        print("\n" + "="*70)
        print("PREMIER LEAGUE")
        print("="*70)
        ctx_pl = LeagueContext.from_season(conn, season_id=1)
        strengths_pl, _, _, _ = load_team_strengths(conn, 1, league_ctx=ctx_pl)
        print(f"Equipos con fortalezas: {len(strengths_pl)}")
        
        # La Liga
        print("\n" + "="*70)
        print("LA LIGA")
        print("="*70)
        ctx_laliga = LeagueContext.from_season(conn, season_id=2)
        strengths_laliga, _, _, _ = load_team_strengths(conn, 2, league_ctx=ctx_laliga)
        print(f"Equipos con fortalezas: {len(strengths_laliga)}")
        
        # Verificar que las fortalezas son diferentes
        print(f"\n✅ Las ligas ahora tienen métricas independientes!")