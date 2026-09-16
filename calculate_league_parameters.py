#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calculate_league_parameters.py
==============================
Calcula y guarda parámetros de liga en la tabla league_parameters.

Este script analiza el histórico de partidos de cada liga y calcula:
- avg_home_goals: Promedio de goles del equipo local
- avg_away_goals: Promedio de goles del equipo visitante
- home_field_advantage: Factor de ventaja local (HFA)
- avg_shots: Promedio de tiros por partido
- avg_shots_on_target: Promedio de tiros a puerta
- avg_corners: Promedio de corners
- avg_cards: Promedio de tarjetas
- avg_fouls: Promedio de faltas
- betting_line_shots: Línea de apuestas sugerida para tiros
- betting_line_corners: Línea de apuestas sugerida para corners
- betting_line_cards: Línea de apuestas sugerida para tarjetas
- betting_line_fouls: Línea de apuestas sugerida para faltas

Uso:
    python calculate_league_parameters.py [--league-id ID] [--all] [--env-file FILE]
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from typing import Optional, Dict, Any
import argparse

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_info(msg):
    print(f"{Colors.BLUE}ℹ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_title(msg):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}{Colors.END}\n")


def _get_recent_complete_season_ids(conn, league_id: int, n: int = 2) -> list[int]:
    """
    Las `n` temporadas más recientes de esta liga que ya terminaron por
    completo (sin ningún partido pendiente) - excluye la temporada en curso
    aunque ya lleve varias fechas jugadas, para no mezclar una muestra
    parcial con temporadas completas.
    """
    rows = conn.execute(text("""
        SELECT s.id
        FROM seasons s
        JOIN matches m ON m.season_id = s.id
        WHERE s.league_id = :league_id
        GROUP BY s.id, s.year_start
        HAVING COUNT(*) FILTER (WHERE m.home_goals IS NULL) = 0
           AND COUNT(*) >= 100
        ORDER BY s.year_start DESC
        LIMIT :n
    """), {"league_id": league_id, "n": n}).scalars().all()
    return list(rows)


def calculate_league_parameters(conn, league_id: int, n_seasons: int = 2) -> Optional[Dict[str, Any]]:
    """
    Calcula todos los parámetros estadísticos de una liga, usando solo las
    `n_seasons` temporadas completas más recientes en vez del histórico
    completo - el arbitraje y el estilo de juego cambian con los años (ej.
    Bundesliga: ~30.7 faltas/partido en 2013/14 vs ~20.9 en 2025/26, una
    caída del 32% en 13 temporadas), así que promediar todo el histórico
    por igual produce una línea desactualizada frente al nivel actual.

    Args:
        conn: Conexión a la base de datos
        league_id: ID de la liga
        n_seasons: cuántas temporadas completas recientes usar (default 2)

    Returns:
        Diccionario con los parámetros calculados o None si no hay datos
    """
    season_ids = _get_recent_complete_season_ids(conn, league_id, n_seasons)
    if not season_ids:
        return None

    query = text("""
        SELECT
            s.league_id,
            l.name as league_name,
            COUNT(DISTINCT m.id) as total_matches,

            -- Promedios de goles
            AVG(m.home_goals)::float as avg_home_goals,
            AVG(m.away_goals)::float as avg_away_goals,

            -- Home Field Advantage (ratio home/away)
            CASE
                WHEN AVG(m.away_goals) > 0
                THEN (AVG(m.home_goals) / AVG(m.away_goals))::float
                ELSE 1.05
            END as home_field_advantage,

            -- Estadísticas de match_stats
            AVG(ms.total_shots)::float as avg_shots,
            AVG(ms.total_shots_on_target)::float as avg_shots_on_target,
            AVG(ms.total_corners)::float as avg_corners,
            AVG(ms.total_cards)::float as avg_cards,
            AVG(ms.total_fouls)::float as avg_fouls,

            -- Líneas de apuestas sugeridas (percentil 50 - mediana)
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.total_shots) as betting_line_shots,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.total_corners) as betting_line_corners,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.total_cards) as betting_line_cards,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ms.total_fouls) as betting_line_fouls

        FROM matches m
        JOIN seasons s ON s.id = m.season_id
        JOIN leagues l ON l.id = s.league_id
        LEFT JOIN match_stats ms ON ms.match_id = m.id
        WHERE m.season_id = ANY(:season_ids)
          AND m.home_goals IS NOT NULL
          AND m.away_goals IS NOT NULL
        GROUP BY s.league_id, l.name
        HAVING COUNT(DISTINCT m.id) > 0
    """)

    result = conn.execute(query, {"season_ids": season_ids}).mappings().one_or_none()

    if not result:
        return None

    return dict(result)


def insert_or_update_league_parameters(conn, params: Dict[str, Any]):
    """
    Inserta o actualiza los parámetros de una liga.
    """
    upsert_query = text("""
        INSERT INTO league_parameters (
            league_id,
            avg_home_goals,
            avg_away_goals,
            home_field_advantage,
            avg_shots,
            avg_shots_on_target,
            avg_corners,
            avg_cards,
            avg_fouls,
            betting_line_shots,
            betting_line_corners,
            betting_line_cards,
            betting_line_fouls,
            sample_size,
            last_calculated
        ) VALUES (
            :league_id,
            :avg_home_goals,
            :avg_away_goals,
            :home_field_advantage,
            :avg_shots,
            :avg_shots_on_target,
            :avg_corners,
            :avg_cards,
            :avg_fouls,
            :betting_line_shots,
            :betting_line_corners,
            :betting_line_cards,
            :betting_line_fouls,
            :total_matches,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (league_id) DO UPDATE SET
            avg_home_goals = EXCLUDED.avg_home_goals,
            avg_away_goals = EXCLUDED.avg_away_goals,
            home_field_advantage = EXCLUDED.home_field_advantage,
            avg_shots = EXCLUDED.avg_shots,
            avg_shots_on_target = EXCLUDED.avg_shots_on_target,
            avg_corners = EXCLUDED.avg_corners,
            avg_cards = EXCLUDED.avg_cards,
            avg_fouls = EXCLUDED.avg_fouls,
            betting_line_shots = EXCLUDED.betting_line_shots,
            betting_line_corners = EXCLUDED.betting_line_corners,
            betting_line_cards = EXCLUDED.betting_line_cards,
            betting_line_fouls = EXCLUDED.betting_line_fouls,
            sample_size = EXCLUDED.sample_size,
            last_calculated = EXCLUDED.last_calculated,
            updated_at = CURRENT_TIMESTAMP
    """)
    
    conn.execute(upsert_query, {
        "league_id": params["league_id"],
        "avg_home_goals": params["avg_home_goals"],
        "avg_away_goals": params["avg_away_goals"],
        "home_field_advantage": params["home_field_advantage"],
        "avg_shots": params["avg_shots"],
        "avg_shots_on_target": params["avg_shots_on_target"],
        "avg_corners": params["avg_corners"],
        "avg_cards": params["avg_cards"],
        "avg_fouls": params["avg_fouls"],
        "betting_line_shots": params["betting_line_shots"],
        "betting_line_corners": params["betting_line_corners"],
        "betting_line_cards": params["betting_line_cards"],
        "betting_line_fouls": params["betting_line_fouls"],
        "total_matches": params["total_matches"]
    })


def get_all_leagues(conn):
    """Obtiene todas las ligas con datos."""
    query = text("""
        SELECT DISTINCT
            l.id,
            l.name,
            COUNT(DISTINCT m.id) as match_count
        FROM leagues l
        JOIN seasons s ON s.league_id = l.id
        JOIN matches m ON m.season_id = s.id
        WHERE m.home_goals IS NOT NULL
        GROUP BY l.id, l.name
        HAVING COUNT(DISTINCT m.id) > 0
        ORDER BY l.id
    """)
    
    return conn.execute(query).mappings().all()


def main():
    parser = argparse.ArgumentParser(
        description="Calcula parámetros de liga desde datos históricos"
    )
    parser.add_argument(
        "--league-id",
        type=int,
        help="ID de la liga a calcular (omitir para modo interactivo)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Calcular para todas las ligas"
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="Archivo .env a usar (default: .env)"
    )
    
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        CÁLCULO DE PARÁMETROS DE LIGA (league_parameters)  ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    # Cargar .env
    if not os.path.exists(args.env_file):
        print_error(f"Archivo no encontrado: {args.env_file}")
        sys.exit(1)
    
    load_dotenv(args.env_file)
    print_success(f"Archivo cargado: {args.env_file}")
    
    # Construir DSN
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('DB_PASS')
    
    if not all([db_host, db_name, db_user, db_password]):
        print_error("Variables de BD faltantes")
        sys.exit(1)
    
    dsn = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    engine = create_engine(dsn)
    
    print_info(f"Conectando a: {db_name} @ {db_host}")
    print()
    
    with engine.begin() as conn:
        # Obtener ligas disponibles
        leagues = get_all_leagues(conn)
        
        if not leagues:
            print_error("No se encontraron ligas con datos")
            sys.exit(1)
        
        # Modo: todas las ligas
        if args.all:
            print_title("CALCULANDO TODAS LAS LIGAS")
            league_ids = [l["id"] for l in leagues]
        
        # Modo: una liga específica
        elif args.league_id:
            league_ids = [args.league_id]
            print_title(f"CALCULANDO LIGA ID: {args.league_id}")
        
        # Modo: interactivo
        else:
            print_title("LIGAS DISPONIBLES")
            print(f"{'ID':<5} {'Nombre':<30} {'Partidos':<10}")
            print("─" * 50)
            for league in leagues:
                print(f"{league['id']:<5} {league['name']:<30} {league['match_count']:<10}")
            print()
            
            choice = input(f"{Colors.GREEN}Selecciona ID de liga (o 'all' para todas): {Colors.END}").strip()
            
            if choice.lower() == 'all':
                league_ids = [l["id"] for l in leagues]
            else:
                try:
                    league_ids = [int(choice)]
                except ValueError:
                    print_error("ID inválido")
                    sys.exit(1)
        
        # Procesar cada liga
        print_title("PROCESANDO LIGAS")
        
        success_count = 0
        error_count = 0
        
        for league_id in league_ids:
            try:
                print(f"\n{Colors.CYAN}{'─'*70}{Colors.END}")
                print(f"Procesando league_id = {league_id}")
                print(f"{Colors.CYAN}{'─'*70}{Colors.END}")
                
                # Calcular parámetros
                params = calculate_league_parameters(conn, league_id)
                
                if not params:
                    print_warning(f"No hay datos para league_id={league_id}")
                    error_count += 1
                    continue
                
                # Mostrar resultados
                print(f"\n📊 Resultados para {Colors.BOLD}{params['league_name']}{Colors.END}:")
                print(f"   Partidos analizados: {params['total_matches']}")
                print(f"   Promedio goles local: {params['avg_home_goals']:.3f}")
                print(f"   Promedio goles visitante: {params['avg_away_goals']:.3f}")
                print(f"   HFA (ventaja local): {params['home_field_advantage']:.3f}")
                
                if params['avg_shots']:
                    print(f"\n   Estadísticas adicionales:")
                    print(f"   • Tiros: {params['avg_shots']:.1f} (línea: {params['betting_line_shots']:.1f})")
                    print(f"   • Tiros a puerta: {params['avg_shots_on_target']:.1f}")
                    print(f"   • Corners: {params['avg_corners']:.1f} (línea: {params['betting_line_corners']:.1f})")
                    print(f"   • Tarjetas: {params['avg_cards']:.1f} (línea: {params['betting_line_cards']:.1f})")
                    print(f"   • Faltas: {params['avg_fouls']:.1f} (línea: {params['betting_line_fouls']:.1f})")
                
                # Insertar/actualizar en BD
                insert_or_update_league_parameters(conn, params)
                print_success(f"Parámetros guardados en league_parameters")
                
                success_count += 1
                
            except Exception as e:
                print_error(f"Error procesando league_id={league_id}: {e}")
                error_count += 1
        
        # Resumen
        print_title("RESUMEN")
        print(f"  ✅ Ligas procesadas exitosamente: {success_count}")
        print(f"  ❌ Errores: {error_count}")
        print()
        
        if success_count > 0:
            print_success("¡Parámetros calculados y guardados!")
            print_info("Ahora las predicciones usarán estos valores en lugar de cálculos dinámicos")


if __name__ == "__main__":
    main()