#!/usr/bin/env python
"""
Script automatizado para GitHub Actions - Actualización de predicciones multi-liga.

Este script ejecuta las mismas operaciones que update_predictions.py pero sin interacción
del usuario, diseñado para ser ejecutado en CI/CD.

Uso:
    python src/scripts/run_update_automated.py --mode complete --date-from 2024-01-01 --date-to 2024-01-07 --leagues all
    python src/scripts/run_update_automated.py --mode finish --date-from 2024-01-01 --date-to 2024-01-07 --leagues "E0,SP1"
    python src/scripts/run_update_automated.py --mode predict --date-from 2024-01-01 --date-to 2024-01-07 --leagues all
"""

import sys
import os
import argparse
from datetime import datetime
from typing import List
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Importar funciones del script original
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.scripts.league_manager import LeagueManager, LeagueConfig, Colors
from src.predictions.league_context import LeagueContext
from src.predictions.upcoming_poisson import predict_and_upsert_poisson
from src.predictions.upcoming_weinston import predict_and_upsert_weinston
import subprocess
import requests


def print_step(msg: str):
    print(f"\n{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{msg}{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}")


def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")


def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")


def print_info(msg: str):
    print(f"{Colors.BLUE}ℹ️  {msg}{Colors.END}")


def setup_database(env_file: str):
    """Configura la conexión a la base de datos"""
    print_step("🔧 CONFIGURANDO BASE DE DATOS")

    if not os.path.exists(env_file):
        print_error(f"Archivo no encontrado: {env_file}")
        sys.exit(1)

    print_success(f"Archivo encontrado: {env_file}")

    # Limpiar variables de entorno previas
    env_vars_to_clear = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER',
        'DB_PASSWORD', 'DB_PASS', 'DB_SCHEMA', 'DATABASE_URL'
    ]
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]

    # Cargar variables de entorno
    load_dotenv(env_file, override=True)

    # Obtener credenciales
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_database = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('DB_PASS')

    # Validar variables
    missing_vars = []
    if not db_host:
        missing_vars.append('DB_HOST')
    if not db_database:
        missing_vars.append('DB_NAME')
    if not db_user:
        missing_vars.append('DB_USER')
    if not db_password:
        missing_vars.append('DB_PASSWORD o DB_PASS')

    if missing_vars:
        print_error(f"Variables de entorno faltantes en {env_file}:")
        for var in missing_vars:
            print(f"   ❌ {var}")
        sys.exit(1)

    # Construir URL de conexión
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}"

    # Crear engine
    try:
        engine = create_engine(database_url)

        # Probar conexión
        print_info("Probando conexión...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()")).scalar()

        print_success("✅ Conexión exitosa")
        print(f"\n{Colors.BOLD}Detalles de conexión:{Colors.END}")
        print(f"  • Host: {db_host}")
        print(f"  • Puerto: {db_port}")
        print(f"  • Database: {db_database}")
        print(f"  • Usuario: {db_user}")
        print(f"  • Estado: {Colors.GREEN}Conectado ✓{Colors.END}\n")

        return engine

    except Exception as e:
        print_error(f"Error al conectar a la base de datos")
        print(f"\n{Colors.RED}Detalles del error:{Colors.END}")
        print(f"  {str(e)}\n")
        sys.exit(1)


def get_leagues(engine, leagues_param: str) -> List[LeagueConfig]:
    """Obtiene las ligas a procesar"""
    print_step("🏆 SELECCIONANDO LIGAS")

    with engine.begin() as conn:
        manager = LeagueManager(conn)

        if leagues_param.lower() == "all":
            # Obtener todas las ligas disponibles
            all_leagues = manager.get_all_leagues()
            print_success(f"Procesando TODAS las ligas ({len(all_leagues)})")
            for league in all_leagues:
                print(f"  • {league.league_name}")
            return all_leagues
        else:
            # Parsear códigos de ligas separados por coma
            league_codes = [code.strip() for code in leagues_param.split(',')]
            selected_leagues = []

            all_leagues = manager.get_all_leagues()

            for code in league_codes:
                league = next((l for l in all_leagues if l.csv_code == code), None)
                if league:
                    selected_leagues.append(league)
                    print_success(f"Liga encontrada: {league.league_name} ({code})")
                else:
                    print_warning(f"Liga no encontrada: {code}")

            if not selected_leagues:
                print_error("No se encontraron ligas válidas")
                sys.exit(1)

            return selected_leagues


def mode_predict_auto(engine, league_config: LeagueConfig, date_from: str, date_to: str) -> bool:
    """Modo: Generar predicciones (versión automatizada)"""
    print_step(f"🎯 GENERAR PREDICCIONES - {league_config.league_name}")

    season_id = league_config.season_id

    # Verificar partidos sin resultados
    query = text("""
        SELECT id, date, home_team_id, away_team_id
        FROM matches
        WHERE season_id = :sid
          AND date BETWEEN :dfrom AND :dto
          AND home_goals IS NULL
          AND away_goals IS NULL
        ORDER BY date
    """)

    with engine.begin() as conn:
        rows = conn.execute(query, {"sid": season_id, "dfrom": date_from, "dto": date_to}).fetchall()
        count = len(rows)

    if count == 0:
        print_warning(f"No hay partidos sin resultados para {league_config.league_name}")
        return False

    print_success(f"Hay {count} partidos sin resultados")

    # Generar predicciones
    try:
        match_ids = [row.id for row in rows]

        with engine.begin() as conn:
            league_ctx = LeagueContext.from_season(conn, season_id)

            print_info(f"Contexto cargado: {league_ctx.league_name}")

            print_info("Generando predicciones Poisson...")
            predict_and_upsert_poisson(conn, season_id, match_ids, league_ctx=league_ctx)
            print_success("✓ Poisson completado")

            print_info("Generando predicciones Weinston...")
            predict_and_upsert_weinston(conn, season_id, match_ids, league_ctx=league_ctx)
            print_success("✓ Weinston completado")

        print_success(f"✅ {count} predicciones generadas para {league_config.league_name}")
        return True

    except Exception as e:
        print_error(f"Error al generar predicciones: {e}")
        import traceback
        traceback.print_exc()
        return False


def mode_retrain_auto(engine, league_config: LeagueConfig, env_file: str) -> bool:
    """Modo: Re-entrenar modelo Weinston (versión automatizada)"""
    print_step(f"🔄 RE-ENTRENAR WEINSTON - {league_config.league_name}")

    env = os.environ.copy()
    env['ENV_FILE'] = env_file

    cmd = f"python -m src.predictions.cli fit --season-id {league_config.season_id}"

    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")

    result = subprocess.run(cmd, shell=True, env=env)

    if result.returncode == 0:
        print_success(f"Weinston re-entrenado para {league_config.league_name}")
        return True
    else:
        print_error("Error al re-entrenar Weinston")
        return False


def generate_betting_lines_auto(engine, league_config: LeagueConfig, date_from: str, date_to: str, env_file: str) -> bool:
    """Genera líneas de apuesta (versión automatizada)"""
    print_info(f"Generando betting lines para {league_config.league_name}...")

    env = os.environ.copy()
    env['ENV_FILE'] = env_file

    cmd = (
        f"python -m src.predictions.cli betting-lines "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )

    result = subprocess.run(cmd, shell=True, env=env)

    if result.returncode == 0:
        print_success(f"Betting lines generadas para {league_config.league_name}")
        return True
    return False


def generate_best_bets_auto(league_config: LeagueConfig, date_from: str, date_to: str, env_file: str) -> bool:
    """Genera mejores apuestas (versión automatizada)"""
    print_step(f"🎯 GENERANDO BEST BETS - {league_config.league_name}")

    try:
        if env_file == ".env":
            api_url = os.getenv('API_URL', 'http://localhost:8000')
        else:
            api_url = os.getenv('API_URL')
            if not api_url:
                print_error(f"API_URL no encontrada en {env_file}")
                return False

        params = {
            'top_n': 4,
            'min_confidence': 0.0
        }

        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to

        endpoint = f"{api_url}/api/best-bets/analysis-multiliga"
        print_info(f"Llamando a: {endpoint}")

        response = requests.get(endpoint, params=params, timeout=30)

        if response.status_code == 200:
            result = response.json()

            if result.get('status') == 'success':
                print_success("✅ Best Bets generadas exitosamente")
                return True
            else:
                print_error(f"Error en respuesta: {result.get('message', 'Unknown error')}")
                return False
        else:
            print_error(f"Error HTTP {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Error generando best bets: {e}")
        return False


def mode_load_results_auto(engine, league_config: LeagueConfig, env_file: str) -> bool:
    """Modo: Cargar resultados desde CSV (versión automatizada)"""
    print_step(f"📥 CARGAR RESULTADOS - {league_config.league_name}")

    # Default CSV path
    csv_path = f"data/raw/{league_config.csv_code}.csv"

    if not os.path.exists(csv_path):
        print_warning(f"CSV no encontrado: {csv_path}")
        return False

    print_info(f"Cargando desde: {csv_path}")

    env = os.environ.copy()
    env['ENV_FILE'] = env_file

    cmd = (
        f"python -m src.ingest.load_unified {csv_path} "
        f"--league \"{league_config.league_name}\" "
        f"--div {league_config.csv_code} "
        f"--season-id {league_config.season_id} "
    )

    if league_config.dayfirst:
        cmd += "--dayfirst"

    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")

    result = subprocess.run(cmd, shell=True, env=env)

    if result.returncode == 0:
        print_success(f"Resultados cargados para {league_config.league_name}")
        return True
    else:
        print_error("Error al cargar resultados")
        return False


def mode_load_fixtures_auto(league_config: LeagueConfig, env_file: str) -> bool:
    """Modo: Cargar fixtures desde CSV (versión automatizada)"""
    print_step(f"📥 CARGAR FIXTURES - {league_config.league_name}")

    # Default fixtures CSV path
    fixtures_path = f"data/fixtures_{league_config.csv_code}.csv"

    if not os.path.exists(fixtures_path):
        print_warning(f"CSV de fixtures no encontrado: {fixtures_path}")
        return False

    print_info(f"Cargando fixtures desde: {fixtures_path}")

    env = os.environ.copy()
    env['ENV_FILE'] = env_file

    cmd = (
        f"python -m src.fixtures.cli bulk {fixtures_path} "
        f"--season-id {league_config.season_id} "
        f"--league \"{league_config.league_name}\""
    )

    if league_config.dayfirst:
        cmd += " --dayfirst"

    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")

    result = subprocess.run(cmd, shell=True, env=env)

    if result.returncode == 0:
        print_success(f"Fixtures cargados para {league_config.league_name}")
        return True
    else:
        print_error("Error al cargar fixtures")
        return False


def mode_evaluate_auto(engine, league_config: LeagueConfig, date_from: str, date_to: str, env_file: str) -> bool:
    """Modo: Evaluar predicciones (versión automatizada)"""
    print_step(f"📊 EVALUAR PREDICCIONES - {league_config.league_name}")

    env = os.environ.copy()
    env['ENV_FILE'] = env_file

    cmd = (
        f"python -m src.predictions.cli evaluate "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )

    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")

    result = subprocess.run(cmd, shell=True, env=env)

    if result.returncode == 0:
        print_success(f"Evaluación completada para {league_config.league_name}")
        return True
    else:
        print_error("Error al evaluar predicciones")
        return False


def validate_betting_lines_auto(engine, league_config: LeagueConfig, date_from: str, date_to: str, env_file: str) -> bool:
    """Valida líneas de apuesta (versión automatizada)"""
    print_info(f"Validando betting lines para {league_config.league_name}...")

    env = os.environ.copy()
    env['ENV_FILE'] = env_file

    cmd = (
        f"python -m src.predictions.cli betting-lines-validate "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )

    result = subprocess.run(cmd, shell=True, env=env)

    if result.returncode == 0:
        print_success(f"Betting lines validadas para {league_config.league_name}")
        return True
    return False


def validate_best_bets_auto(league_config: LeagueConfig, env_file: str) -> bool:
    """Valida best bets (versión automatizada)"""
    print_step(f"✅ VALIDANDO BEST BETS - {league_config.league_name}")

    try:
        if env_file == ".env":
            api_url = os.getenv('API_URL', 'http://localhost:8000')
        else:
            api_url = os.getenv('API_URL')
            if not api_url:
                print_error(f"API_URL no encontrada en {env_file}")
                return False

        endpoint = f"{api_url}/api/best-bets/validate"
        params = {'season_id': league_config.season_id}

        response = requests.post(endpoint, params=params, timeout=30)

        if response.status_code == 200:
            result = response.json()

            if result.get('success'):
                print_success("✅ Validación completada")
                return True
            else:
                print_warning("No hay best bets pendientes de validar")
                return True
        else:
            print_error(f"Error HTTP {response.status_code}")
            return False

    except Exception as e:
        print_error(f"Error validando best bets: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Actualización automatizada de predicciones')
    parser.add_argument('--mode', required=True,
                       choices=['complete', 'finish', 'predict', 'retrain', 'best-bets'],
                       help='Modo de operación')
    parser.add_argument('--date-from', help='Fecha desde (YYYY-MM-DD)')
    parser.add_argument('--date-to', help='Fecha hasta (YYYY-MM-DD)')
    parser.add_argument('--leagues', default='all',
                       help='Ligas a procesar (all o códigos separados por coma: E0,SP1,D1,I1)')
    parser.add_argument('--env-file', default='.env.production',
                       help='Archivo de configuración (.env o .env.production)')

    args = parser.parse_args()

    # Validar fechas si son requeridas
    if args.mode in ['complete', 'finish', 'predict', 'best-bets']:
        if not args.date_from or not args.date_to:
            print_error(f"El modo '{args.mode}' requiere --date-from y --date-to")
            sys.exit(1)

        try:
            datetime.strptime(args.date_from, "%Y-%m-%d")
            datetime.strptime(args.date_to, "%Y-%m-%d")
        except ValueError:
            print_error("Formato de fecha inválido (usar YYYY-MM-DD)")
            sys.exit(1)

    # Configurar base de datos
    engine = setup_database(args.env_file)

    # Obtener ligas
    leagues = get_leagues(engine, args.leagues)

    # Resumen de operación
    print(f"\n{Colors.YELLOW}{'─'*70}{Colors.END}")
    print(f"{Colors.BOLD}OPERACIÓN:{Colors.END}")
    print(f"  • Modo: {args.mode}")
    print(f"  • Ligas: {len(leagues)}")
    print(f"  • Fechas: {args.date_from} → {args.date_to}" if args.date_from else "  • Fechas: N/A")
    print(f"{Colors.YELLOW}{'─'*70}{Colors.END}\n")

    # Ejecutar operaciones
    success_count = 0
    failed_leagues = []

    for idx, league_config in enumerate(leagues, 1):
        print(f"\n{Colors.BOLD}{Colors.CYAN}[{idx}/{len(leagues)}] {league_config.league_name}{Colors.END}")

        success = False

        try:
            if args.mode == 'complete':
                # Flujo: LOAD FIXTURES → RETRAIN → PREDICT → BETTING LINES → BEST BETS
                if mode_load_fixtures_auto(league_config, args.env_file):
                    if mode_retrain_auto(engine, league_config, args.env_file):
                        if mode_predict_auto(engine, league_config, args.date_from, args.date_to):
                            if generate_betting_lines_auto(engine, league_config, args.date_from, args.date_to, args.env_file):
                                generate_best_bets_auto(league_config, args.date_from, args.date_to, args.env_file)
                                success = True

            elif args.mode == 'finish':
                # Flujo: LOAD RESULTS → EVALUATE → VALIDATE BETTING → VALIDATE BEST BETS
                if mode_load_results_auto(engine, league_config, args.env_file):
                    if mode_evaluate_auto(engine, league_config, args.date_from, args.date_to, args.env_file):
                        if validate_betting_lines_auto(engine, league_config, args.date_from, args.date_to, args.env_file):
                            validate_best_bets_auto(league_config, args.env_file)
                            success = True

            elif args.mode == 'predict':
                success = mode_predict_auto(engine, league_config, args.date_from, args.date_to)

            elif args.mode == 'retrain':
                success = mode_retrain_auto(engine, league_config, args.env_file)

            elif args.mode == 'best-bets':
                success = generate_best_bets_auto(league_config, args.date_from, args.date_to, args.env_file)

            if success:
                print_success(f"✓ {league_config.league_name} completada")
                success_count += 1
            else:
                print_warning(f"⚠️  {league_config.league_name} con advertencias")
                failed_leagues.append(league_config.league_name)

        except Exception as e:
            print_error(f"Error en {league_config.league_name}: {e}")
            failed_leagues.append(league_config.league_name)
            continue

    # Resumen final
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}  RESUMEN{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")

    print(f"  Ligas procesadas: {success_count}/{len(leagues)}")

    if success_count == len(leagues):
        print_success("✅ Todas las ligas procesadas exitosamente")
        sys.exit(0)
    elif success_count > 0:
        print_warning(f"⚠️  {len(failed_leagues)} liga(s) con problemas:")
        for league_name in failed_leagues:
            print(f"     • {league_name}")
        sys.exit(1)
    else:
        print_error("❌ No se pudo procesar ninguna liga")
        sys.exit(1)


if __name__ == "__main__":
    main()
