# src/predictions/league_context.py
"""
Módulo para gestionar el contexto de ligas/competiciones.

Este módulo proporciona una abstracción para trabajar con múltiples ligas
de forma independiente, utilizando las tablas existentes:
- leagues: Catálogo de ligas
- seasons: Temporadas con league_id
- weinston_params: Parámetros por temporada
- league_parameters: Promedios agregados por liga
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.engine import Connection


@dataclass
class LeagueContext:
    """
    Contexto de liga para predicciones.
    
    Encapsula toda la información específica de una liga/competición
    para garantizar que las predicciones sean independientes entre ligas.
    
    Attributes:
        league_id: ID de la liga/competición
        league_name: Nombre de la liga (ej: "Premier League", "La Liga")
        season_id: ID de la temporada actual
        season_year: Año de la temporada (ej: "2024/2025")
        avg_home_goals: Promedio de goles en casa para esta liga
        avg_away_goals: Promedio de goles de visitante para esta liga
        hfa: Home Field Advantage (factor multiplicador)
    """
    league_id: int
    league_name: str
    season_id: int
    season_year: str
    avg_home_goals: float
    avg_away_goals: float
    hfa: float
    
    @classmethod
    def from_season(cls, conn: Connection, season_id: int) -> 'LeagueContext':
        """
        Carga el contexto completo de liga desde un season_id.
        
        Prioridad de carga de parámetros:
        1. weinston_params (específico por temporada) ← Más específico
        2. league_parameters (promedio por liga)
        3. Cálculo dinámico (fallback)
        
        Args:
            conn: Conexión a la base de datos
            season_id: ID de la temporada
            
        Returns:
            LeagueContext con todos los parámetros cargados
            
        Raises:
            ValueError: Si el season_id no existe o no tiene league_id
        """
        # Intentar cargar desde weinston_params primero (más específico)
        query = text("""
            SELECT 
                s.id as season_id,
                s.year_start || '/' || s.year_end as season_year,
                l.id as league_id,
                l.name as league_name,
                l.country,
                wp.mu_home as wp_mu_home,
                wp.mu_away as wp_mu_away,
                wp.home_adv as wp_home_adv,
                lp.avg_home_goals as lp_avg_home,
                lp.avg_away_goals as lp_avg_away,
                lp.home_field_advantage as lp_hfa
            FROM seasons s
            JOIN leagues l ON l.id = s.league_id
            LEFT JOIN weinston_params wp ON wp.season_id = s.id
            LEFT JOIN league_parameters lp ON lp.league_id = l.id
            WHERE s.id = :season_id
        """)
        
        try:
            row = conn.execute(query, {"season_id": season_id}).one()
        except Exception as e:
            raise ValueError(
                f"No se pudo cargar información para season_id={season_id}. "
                f"Asegúrate de que existe y tiene league_id asignado. Error: {e}"
            )
        
        # Prioridad 1: weinston_params (si existe)
        if row.wp_mu_home is not None:
            avg_home = float(row.wp_mu_home)
            avg_away = float(row.wp_mu_away)
            hfa = float(row.wp_home_adv or 1.05)
            source = "weinston_params (temporada específica)"
        
        # Prioridad 2: league_parameters (si existe)
        elif row.lp_avg_home is not None:
            avg_home = float(row.lp_avg_home)
            avg_away = float(row.lp_avg_away)
            hfa = float(row.lp_hfa or 1.05)
            source = "league_parameters (promedio de liga)"
        
        # Prioridad 3: Cálculo dinámico (fallback)
        else:
            print(f"⚠️  No hay parámetros precalculados para {row.league_name}")
            print(f"   Calculando desde datos históricos...")
            avg_home, avg_away = cls._calculate_league_averages(
                conn, row.league_id
            )
            hfa = 1.05
            source = "cálculo dinámico"
        
        print(f"✅ Contexto cargado desde: {source}")
        print(f"   Liga: {row.league_name}")
        print(f"   Promedios: {avg_home:.3f} (H) / {avg_away:.3f} (A)")
        print(f"   HFA: {hfa:.3f}")
        
        return cls(
            league_id=row.league_id,
            league_name=row.league_name,
            season_id=season_id,
            season_year=row.season_year,
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            hfa=hfa
        )
    
    @staticmethod
    def _calculate_league_averages(
        conn: Connection, 
        league_id: int
    ) -> Tuple[float, float]:
        """
        Calcula promedios de goles de una liga desde datos históricos.
        
        Args:
            conn: Conexión a la base de datos
            league_id: ID de la liga
            
        Returns:
            Tuple (avg_home_goals, avg_away_goals)
        """
        query = text("""
            SELECT 
                AVG(m.home_goals)::float as avg_home,
                AVG(m.away_goals)::float as avg_away,
                COUNT(*) as sample_size
            FROM matches m
            JOIN seasons s ON s.id = m.season_id
            WHERE s.league_id = :league_id
              AND m.home_goals IS NOT NULL
              AND m.away_goals IS NOT NULL
              AND m.date < CURRENT_DATE
        """)
        
        row = conn.execute(query, {"league_id": league_id}).one()
        
        if row.sample_size == 0:
            print(f"⚠️  No hay datos históricos para league_id={league_id}")
            print(f"   Usando valores por defecto (1.4, 1.1)")
            return 1.4, 1.1
        
        print(f"✅ Promedios calculados desde {row.sample_size} partidos")
        return row.avg_home or 1.4, row.avg_away or 1.1
    
    def __str__(self) -> str:
        return (
            f"LeagueContext("
            f"league='{self.league_name}', "
            f"season='{self.season_year}', "
            f"avg_goals={self.avg_home_goals:.2f}/{self.avg_away_goals:.2f}, "
            f"hfa={self.hfa:.2f})"
        )
    
    def __repr__(self) -> str:
        return self.__str__()


def get_league_id(conn: Connection, season_id: int) -> int:
    """
    Helper: Obtiene el league_id de un season_id.
    
    Args:
        conn: Conexión a la base de datos
        season_id: ID de la temporada
        
    Returns:
        league_id
        
    Raises:
        ValueError: Si el season_id no existe o no tiene league_id
    """
    query = text("SELECT league_id FROM seasons WHERE id = :sid")
    result = conn.execute(query, {"sid": season_id}).scalar()
    
    if result is None:
        raise ValueError(
            f"season_id={season_id} no existe o no tiene league_id asignado"
        )
    
    return result


def get_all_leagues(conn: Connection) -> list[Dict[str, Any]]:
    """
    Obtiene todas las ligas con información resumida.
    
    Args:
        conn: Conexión a la base de datos
        
    Returns:
        Lista de diccionarios con información de ligas
    """
    query = text("""
        SELECT 
            l.id,
            l.name,
            l.country,
            COUNT(DISTINCT s.id) as seasons_count,
            MIN(s.year_start) as first_season,
            MAX(s.year_start) as latest_season,
            COUNT(DISTINCT m.id) as total_matches
        FROM leagues l
        LEFT JOIN seasons s ON s.league_id = l.id
        LEFT JOIN matches m ON m.season_id = s.id
        GROUP BY l.id, l.name, l.country
        HAVING COUNT(DISTINCT s.id) > 0  -- Solo ligas con temporadas
        ORDER BY l.name
    """)
    
    rows = conn.execute(query).mappings().all()
    return [dict(r) for r in rows]


def get_seasons_by_league(
    conn: Connection, 
    league_id: int
) -> list[Dict[str, Any]]:
    """
    Obtiene todas las temporadas de una liga.
    
    Args:
        conn: Conexión a la base de datos
        league_id: ID de la liga
        
    Returns:
        Lista de diccionarios con información de temporadas
    """
    query = text("""
        SELECT 
            s.id,
            s.year_start || '/' || s.year_end as season_name,
            s.year_start,
            s.year_end,
            s.league_id,
            l.name as league_name,
            COUNT(m.id) as matches_count,
            MIN(m.date) as first_match,
            MAX(m.date) as last_match
        FROM seasons s
        JOIN leagues l ON l.id = s.league_id
        LEFT JOIN matches m ON m.season_id = s.id
        WHERE s.league_id = :league_id
        GROUP BY s.id, s.year_start, s.year_end, s.league_id, l.name
        ORDER BY s.year_start DESC
    """)
    
    rows = conn.execute(query, {"league_id": league_id}).mappings().all()
    return [dict(r) for r in rows]


def get_active_leagues(conn: Connection, min_matches: int = 100) -> list[Dict[str, Any]]:
    """
    Obtiene solo las ligas con suficientes datos para hacer predicciones.
    
    Args:
        conn: Conexión a la base de datos
        min_matches: Mínimo de partidos históricos necesarios
        
    Returns:
        Lista de ligas activas
    """
    query = text("""
        SELECT 
            l.id,
            l.name,
            l.country,
            COUNT(DISTINCT m.id) as total_matches,
            MAX(s.year_start) as latest_season
        FROM leagues l
        JOIN seasons s ON s.league_id = l.id
        JOIN matches m ON m.season_id = s.id
        WHERE m.home_goals IS NOT NULL
        GROUP BY l.id, l.name, l.country
        HAVING COUNT(DISTINCT m.id) >= :min_matches
        ORDER BY total_matches DESC
    """)
    
    rows = conn.execute(query, {"min_matches": min_matches}).mappings().all()
    return [dict(r) for r in rows]


# Ejemplo de uso
if __name__ == "__main__":
    from sqlalchemy import create_engine
    from src.config import settings
    
    engine = create_engine(settings.sqlalchemy_url)
    
    with engine.begin() as conn:
        print("="*70)
        print("EJEMPLO DE USO: league_context.py")
        print("="*70)
        
        # 1. Listar ligas activas
        print("\n1. LIGAS ACTIVAS:")
        active = get_active_leagues(conn)
        for league in active:
            print(f"   - {league['name']:20} ({league['country']:15}): {league['total_matches']:,} partidos")
        
        # 2. Cargar contexto de Premier League (asumiendo season_id=7)
        print("\n2. CARGAR CONTEXTO - PREMIER LEAGUE:")
        try:
            ctx_pl = LeagueContext.from_season(conn, season_id=7)
            print(f"   {ctx_pl}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 3. Cargar contexto de La Liga (asumiendo season_id=15)
        print("\n3. CARGAR CONTEXTO - LA LIGA:")
        try:
            ctx_laliga = LeagueContext.from_season(conn, season_id=15)
            print(f"   {ctx_laliga}")
        except Exception as e:
            print(f"   Error: {e}")
        
        # 4. Verificar independencia
        print("\n4. VERIFICAR INDEPENDENCIA:")
        if 'ctx_pl' in locals() and 'ctx_laliga' in locals():
            print(f"   Premier League avg: {ctx_pl.avg_home_goals:.3f}")
            print(f"   La Liga avg:        {ctx_laliga.avg_home_goals:.3f}")
            print(f"   ¿Son diferentes? {'✅ SÍ' if abs(ctx_pl.avg_home_goals - ctx_laliga.avg_home_goals) > 0.01 else '❌ NO'}")