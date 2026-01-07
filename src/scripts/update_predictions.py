#!/usr/bin/env python
"""
Script inteligente para actualizar predicciones - VERSIÓN MULTI-LIGA.
Valida el estado del sistema antes de ejecutar comandos.

CAMBIOS:
- Selector de base de datos al inicio (localhost o producción)
- Resto del código sin cambios (usa subprocess como el original)
"""
import sys
import os
from datetime import datetime
from typing import Tuple, Optional, List
from sqlalchemy import text, create_engine
from dotenv import load_dotenv
import requests
import subprocess

# League Manager
from src.scripts.league_manager import (
    LeagueManager, 
    LeagueConfig, 
    print_league_header,
    Colors
)

# Contexto de liga
from src.predictions.league_context import LeagueContext

# Funciones de predicción
from src.predictions.upcoming_poisson import predict_and_upsert_poisson
from src.predictions.upcoming_weinston import predict_and_upsert_weinston


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VARIABLE GLOBAL PARA EL ENGINE (como en el original)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

engine = None  # Se inicializa en select_database()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SELECTOR DE BASE DE DATOS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def select_database():
    """
    Permite al usuario seleccionar entre localhost o producción.
    Retorna el engine configurado y el nombre de la BD seleccionada.
    """
    global engine
    
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     55sportsBet - Actualización Inteligente MULTI-LIGA    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    print(f"\n{Colors.BOLD}SELECCIÓN DE BASE DE DATOS{Colors.END}")
    print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
    
    print("  1. 🏠 LOCALHOST  - Base de datos local (desarrollo)")
    print("  2. 🌐 PRODUCCIÓN - Base de datos en Render (producción)")
    print("  0. ❌ SALIR\n")
    
    choice = input(f"{Colors.GREEN}Selecciona la base de datos a usar (0-2): {Colors.END}").strip()
    
    if choice == "0":
        print_info("Saliendo...")
        sys.exit(0)
    
    if choice not in ["1", "2"]:
        print_error("Opción inválida")
        sys.exit(1)
    
    # Determinar archivo .env
    if choice == "1":
        env_file = ".env"
        db_name = "LOCALHOST"
        db_emoji = "🏠"
    else:
        env_file = ".env.production"
        db_name = "PRODUCCIÓN"
        db_emoji = "🌐"
    
    print(f"\n{Colors.CYAN}{'─'*70}{Colors.END}")
    print(f"{db_emoji} Configurando conexión a {Colors.BOLD}{db_name}{Colors.END}...")
    print(f"{Colors.CYAN}{'─'*70}{Colors.END}\n")
    
    # Verificar que el archivo existe
    if not os.path.exists(env_file):
        print_error(f"Archivo no encontrado: {env_file}")
        print_info("Asegúrate de tener el archivo de configuración en la raíz del proyecto")
        print_info(f"Ruta esperada: {os.path.abspath(env_file)}")
        sys.exit(1)
    
    print_success(f"Archivo encontrado: {env_file}")
    
    # IMPORTANTE: Limpiar variables de entorno previas
    env_vars_to_clear = [
        'DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 
        'DB_PASSWORD', 'DB_PASS', 'DB_SCHEMA', 'DATABASE_URL'
    ]
    for var in env_vars_to_clear:
        if var in os.environ:
            del os.environ[var]
    
    # Cargar variables de entorno
    load_dotenv(env_file, override=True)
    
    # Obtener credenciales (soporta DB_PASS y DB_PASSWORD)
    db_host = os.getenv('DB_HOST')
    db_port = os.getenv('DB_PORT', '5432')
    db_database = os.getenv('DB_NAME')
    db_user = os.getenv('DB_USER')
    db_password = os.getenv('DB_PASSWORD') or os.getenv('DB_PASS')
    
    # Validar que todas las variables estén presentes
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
        print()
        print_info("Tu archivo .env debe contener:")
        print("   DB_HOST=...")
        print("   DB_PORT=...")
        print("   DB_NAME=...")
        print("   DB_USER=...")
        print("   DB_PASSWORD=...  (o DB_PASS=...)")
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
            
        print_success(f"✅ Conexión exitosa a {db_name}")
        print(f"\n{Colors.BOLD}Detalles de conexión:{Colors.END}")
        print(f"  • Base de datos: {db_name}")
        print(f"  • Host: {db_host}")
        print(f"  • Puerto: {db_port}")
        print(f"  • Database: {db_database}")
        print(f"  • Usuario: {db_user}")
        print(f"  • Estado: {Colors.GREEN}Conectado ✓{Colors.END}\n")
        
        return db_name, env_file
        
    except Exception as e:
        print_error(f"Error al conectar a {db_name}")
        print(f"\n{Colors.RED}Detalles del error:{Colors.END}")
        print(f"  {str(e)}\n")
        print_info("Verifica:")
        print("  1. Las credenciales en tu archivo .env")
        print("  2. Que el servidor de base de datos esté accesible")
        print("  3. Que tengas conectividad de red (si es producción)")
        sys.exit(1)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCIONES AUXILIARES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCIONES DE VERIFICACIÓN (ORIGINALES SIN CAMBIOS)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_matches_without_results(season_id: int, date_from: str, date_to: str) -> Tuple[int, list]:
    """Verifica partidos sin resultados en el rango de fechas"""
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
        return len(rows), rows

def check_matches_with_results(season_id: int, date_from: str, date_to: str) -> Tuple[int, list]:
    """Verifica partidos CON resultados en el rango de fechas"""
    query = text("""
        SELECT id, date, home_team_id, away_team_id, home_goals, away_goals
        FROM matches
        WHERE season_id = :sid
          AND date BETWEEN :dfrom AND :dto
          AND home_goals IS NOT NULL
          AND away_goals IS NOT NULL
        ORDER BY date
    """)
    
    with engine.begin() as conn:
        rows = conn.execute(query, {"sid": season_id, "dfrom": date_from, "dto": date_to}).fetchall()
        return len(rows), rows

def check_predictions_exist(match_ids: list) -> dict:
    """Verifica si ya existen predicciones para los partidos"""
    if not match_ids:
        return {"poisson": 0, "weinston": 0}
    
    query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM poisson_predictions WHERE match_id = m.id
            )) as poisson_count,
            COUNT(*) FILTER (WHERE EXISTS (
                SELECT 1 FROM weinston_predictions WHERE match_id = m.id
            )) as weinston_count
        FROM matches m
        WHERE m.id = ANY(:ids)
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query, {"ids": match_ids}).fetchone()
        return {"poisson": row.poisson_count, "weinston": row.weinston_count}

def check_weinston_params(season_id: int) -> Optional[dict]:
    """Verifica si existen parámetros de Weinston para la temporada"""
    query = text("""
        SELECT mu_home, mu_away, home_adv, loss, updated_at
        FROM weinston_params
        WHERE season_id = :sid
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query, {"sid": season_id}).fetchone()
        if row:
            return {
                "mu_home": float(row.mu_home),
                "mu_away": float(row.mu_away),
                "home_adv": float(row.home_adv),
                "loss": float(row.loss),
                "updated_at": row.updated_at
            }
        return None

def check_evaluated_matches(season_id: int, date_from: str, date_to: str) -> dict:
    """Verifica cuántos partidos ya fueron evaluados"""
    query = text("""
        SELECT 
            COUNT(DISTINCT po.match_id) FILTER (WHERE po.model = 'poisson') as poisson_evaluated,
            COUNT(DISTINCT po.match_id) FILTER (WHERE po.model = 'weinston') as weinston_evaluated
        FROM prediction_outcomes po
        JOIN matches m ON m.id = po.match_id
        WHERE m.season_id = :sid
          AND m.date BETWEEN :dfrom AND :dto
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query, {"sid": season_id, "dfrom": date_from, "dto": date_to}).fetchone()
        return {
            "poisson": row.poisson_evaluated or 0,
            "weinston": row.weinston_evaluated or 0
        }

def check_fixtures_file(filepath: str) -> bool:
    """Verifica si el archivo de fixtures existe"""
    import os
    if not os.path.exists(filepath):
        print_error(f"Archivo no encontrado: {filepath}")
        return False
    print_success(f"Archivo encontrado: {filepath}")
    return True

def preview_csv_fixtures(filepath: str, max_rows: int = 5):
    """Muestra preview del CSV de fixtures"""
    import csv
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        print(f"\n📋 Preview del CSV ({len(rows)} filas totales):")
        print(f"   Columnas: {', '.join(rows[0].keys()) if rows else 'N/A'}")
        print(f"\n   Primeras {min(max_rows, len(rows))} filas:")
        for i, row in enumerate(rows[:max_rows], 1):
            date = row.get('Date', 'N/A')
            home = row.get('HomeTeam', 'N/A')
            away = row.get('AwayTeam', 'N/A')
            print(f"     {i}. {date}: {home} vs {away}")
        
        return len(rows)
    except Exception as e:
        print_error(f"Error al leer CSV: {e}")
        return 0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODOS (CÓDIGO ORIGINAL SIN CAMBIOS)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mode_load_fixtures(league_config: LeagueConfig, env_file: str):
    """Modo: Cargar fixtures desde CSV para una liga específica"""
    print_step(f"📥 MODO: CARGAR FIXTURES - {league_config.league_name}")
    
    # 1. Solicitar ruta del archivo (o usar default)
    default_path = league_config.get_csv_path("data")
    print_info(f"Archivo default: {default_path}")
    print_info("Presiona Enter para usar el default, o ingresa otra ruta")
    
    filepath = input(f"\n{Colors.GREEN}Ruta del archivo [{default_path}]: {Colors.END}").strip()
    
    if not filepath:
        filepath = default_path
    
    # 2. Verificar que existe
    if not check_fixtures_file(filepath):
        return False
    
    # 3. Preview del contenido
    total_rows = preview_csv_fixtures(filepath)
    
    if total_rows == 0:
        print_error("No se pudieron leer filas del CSV")
        return False
    
    # 4. Confirmar
    response = input(f"\n{Colors.GREEN}¿Cargar {total_rows} fixtures para {league_config.league_name}? (s/n): {Colors.END}")
    
    if response.lower() != 's':
        print_info("Carga cancelada")
        return False
    
    # 5. Ejecutar ingest usando subprocess (como el original)
    print_info(f"Cargando fixtures para {league_config.league_name}...")
    
    # Crear entorno con ENV_FILE
    env = os.environ.copy()
    env['ENV_FILE'] = env_file
    
    cmd = (
        f"python -m src.fixtures.cli bulk {filepath} "
        f"--season-id {league_config.season_id} "
        f"--league \"{league_config.league_name}\""
    )
    
    if league_config.dayfirst:
        cmd += " --dayfirst"
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    print_info(f"Usando configuración: {env_file}")
    
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode == 0:
        print_success(f"Fixtures cargados exitosamente para {league_config.league_name}")
        return True
    else:
        print_error("Error al cargar fixtures")
        return False


def mode_predict(league_config: LeagueConfig, date_from: str, date_to: str):
    """Modo: Generar predicciones para partidos sin resultados"""
    print_step(f"🎯 MODO: GENERAR PREDICCIONES - {league_config.league_name}")
    
    season_id = league_config.season_id
    
    # 1. Verificar partidos sin resultados
    count, rows = check_matches_without_results(season_id, date_from, date_to)
    
    if count == 0:
        print_warning(f"No hay partidos sin resultados para {league_config.league_name}")
        return False
    
    print_success(f"Hay {count} partidos sin resultados")
    
    # 2. Verificar parámetros de Weinston
    params = check_weinston_params(season_id)
    
    if not params:
        print_error("No existen parámetros de Weinston para esta temporada")
        print_info("Ejecuta primero el modo RETRAIN")
        return False
    
    print_success(f"Parámetros de Weinston encontrados (última actualización: {params['updated_at']})")
    
    # 3. Verificar predicciones existentes
    match_ids = [row.id for row in rows]
    existing = check_predictions_exist(match_ids)
    
    if existing["poisson"] > 0 or existing["weinston"] > 0:
        print_info(f"Predicciones existentes:")
        print(f"   • Poisson: {existing['poisson']}/{count}")
        print(f"   • Weinston: {existing['weinston']}/{count}")
        print_info("Las predicciones se actualizarán")
        
        response = input(f"\n{Colors.YELLOW}¿Continuar? (s/n): {Colors.END}")
        if response.lower() != 's':
            return False
    
    # 4. Cargar contexto de liga y generar predicciones (LÓGICA ORIGINAL)
    try:
        with engine.begin() as conn:
            league_ctx = LeagueContext.from_season(conn, season_id)
            
            print_info(f"Contexto cargado: {league_ctx.league_name}")
            print(f"   Promedios: {league_ctx.avg_home_goals:.3f} (H) / {league_ctx.avg_away_goals:.3f} (A)")
            print(f"   HFA: {league_ctx.hfa:.3f}")
            
            print_info("\nGenerando predicciones Poisson...")
            predict_and_upsert_poisson(conn, season_id, match_ids, league_ctx=league_ctx)
            print_success(f"✓ Poisson completado")
            
            print_info("Generando predicciones Weinston...")
            predict_and_upsert_weinston(conn, season_id, match_ids, league_ctx=league_ctx)
            print_success(f"✓ Weinston completado")
        
        print_success(f"✅ {count} predicciones generadas para {league_config.league_name}")
        return True
        
    except Exception as e:
        print_error(f"Error al generar predicciones: {e}")
        import traceback
        traceback.print_exc()
        return False


def mode_load_results(league_config: LeagueConfig, env_file: str):
    """Modo: Cargar resultados desde CSV para una liga"""
    print_step(f"📥 MODO: CARGAR RESULTADOS - {league_config.league_name}")
    
    # 1. Solicitar ruta del archivo
    default_path = league_config.get_csv_path("data/raw")
    print_info(f"Archivo default: {default_path}")
    print_info("Presiona Enter para usar el default, o ingresa otra ruta")
    
    filepath = input(f"\n{Colors.GREEN}Ruta del archivo [{default_path}]: {Colors.END}").strip()
    
    if not filepath:
        filepath = default_path
    
    # 2. Verificar que existe
    if not check_fixtures_file(filepath):
        return False
    
    # 3. Preview
    total_rows = preview_csv_fixtures(filepath)
    
    if total_rows == 0:
        return False
    
    # 4. Confirmar
    response = input(f"\n{Colors.GREEN}¿Cargar resultados para {league_config.league_name}? (s/n): {Colors.END}")
    if response.lower() != 's':
        return False
    
    # 5. Ejecutar carga usando subprocess (COMO EL ORIGINAL)
    import subprocess
    import os
    
    # Crear entorno con ENV_FILE
    env = os.environ.copy()
    env['ENV_FILE'] = env_file
    
    cmd = (
        f"python -m src.ingest.load_unified {filepath} "
        f"--league \"{league_config.league_name}\" "
        f"--div {league_config.csv_code} "
        f"--season-id {league_config.season_id} "
    )
    
    if league_config.dayfirst:
        cmd += "--dayfirst"
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    print_info(f"Usando configuración: {env_file}")
    
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode == 0:
        print_success(f"Resultados cargados para {league_config.league_name}")
        return True
    else:
        print_error("Error al cargar resultados")
        return False


def mode_evaluate(league_config: LeagueConfig, date_from: str, date_to: str, env_file: str):
    """Modo: Evaluar predicciones vs resultados reales"""
    print_step(f"📊 MODO: EVALUAR PREDICCIONES - {league_config.league_name}")
    
    season_id = league_config.season_id
    
    # 1. Verificar partidos con resultados
    count, matches = check_matches_with_results(season_id, date_from, date_to)
    
    if count == 0:
        print_warning(f"No hay partidos con resultados para {league_config.league_name}")
        return False
    
    print_success(f"Hay {count} partidos con resultados")
    
    # 2. Verificar evaluaciones previas
    evaluated = check_evaluated_matches(season_id, date_from, date_to)
    
    if evaluated["poisson"] > 0 or evaluated["weinston"] > 0:
        print_info(f"Predicciones ya evaluadas:")
        print(f"   • Poisson: {evaluated['poisson']}/{count}")
        print(f"   • Weinston: {evaluated['weinston']}/{count}")
        print_info("Las evaluaciones se actualizarán")
    
    # 3. Confirmar
    response = input(f"\n{Colors.GREEN}¿Evaluar predicciones? (s/n): {Colors.END}")
    if response.lower() != 's':
        return False
    
    # 4. Ejecutar evaluación usando subprocess (COMO EL ORIGINAL)
    # IMPORTANTE: Establecer ENV_FILE para que el subprocess use la BD correcta
    import subprocess
    
    # Crear entorno con la variable ENV_FILE
    import os
    env = os.environ.copy()
    env['ENV_FILE'] = env_file
    
    cmd = (
        f"python -m src.predictions.cli evaluate "
        f"--season-id {season_id} "
        f"--from {date_from} --to {date_to}"
    )
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    print_info(f"Usando configuración: {env_file}")
    
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode == 0:
        print_success(f"Evaluación completada para {league_config.league_name}")
        return True
    else:
        print_error("Error al evaluar predicciones")
        return False


def mode_retrain(league_config: LeagueConfig, env_file: str):
    """Modo: Re-entrenar modelo Weinston para una liga"""
    print_step(f"🔄 MODO: RE-ENTRENAR WEINSTON - {league_config.league_name}")
    
    season_id = league_config.season_id
    
    # 1. Verificar partidos terminados
    query = text("""
        SELECT COUNT(*) as total
        FROM matches
        WHERE season_id = :sid
          AND home_goals IS NOT NULL
          AND away_goals IS NOT NULL
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query, {"sid": season_id}).fetchone()
        total_matches = row.total
    
    if total_matches < 10:
        print_warning(f"Solo hay {total_matches} partidos terminados para {league_config.league_name}")
        print_warning("Se recomienda al menos 10 partidos")
        response = input(f"\n{Colors.YELLOW}¿Continuar de todos modos? (s/n): {Colors.END}")
        if response.lower() != 's':
            return False
    
    print_success(f"Hay {total_matches} partidos terminados disponibles para entrenamiento")
    
    # 2. Confirmar
    response = input(f"\n{Colors.GREEN}¿Re-entrenar Weinston para {league_config.league_name}? (s/n): {Colors.END}")
    if response.lower() != 's':
        return False
    
    # 3. Ejecutar entrenamiento usando subprocess (COMO EL ORIGINAL)
    import subprocess
    import os
    
    # Crear entorno con ENV_FILE
    env = os.environ.copy()
    env['ENV_FILE'] = env_file
    
    cmd = f"python -m src.predictions.cli fit --season-id {season_id}"
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    print_info(f"Usando configuración: {env_file}")
    
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode == 0:
        print_success(f"Weinston re-entrenado para {league_config.league_name}")
        return True
    else:
        print_error("Error al re-entrenar Weinston")
        return False


def generate_betting_lines_predictions(league_config: LeagueConfig, date_from: str, date_to: str, env_file: str):
    """Genera líneas de apuesta para los partidos"""
    print_info(f"Generando betting lines para {league_config.league_name}...")
    
    import subprocess
    import os
    
    # Crear entorno con ENV_FILE
    env = os.environ.copy()
    env['ENV_FILE'] = env_file
    
    cmd = (
        f"python -m src.predictions.cli betting-lines "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )
    
    print_info(f"Usando configuración: {env_file}")
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode == 0:
        print_success(f"Betting lines generadas para {league_config.league_name}")
        return True
    return False


def validate_betting_lines_predictions(league_config: LeagueConfig, date_from: str, date_to: str, env_file: str):
    """Valida líneas de apuesta contra resultados reales"""
    print_info(f"Validando betting lines para {league_config.league_name}...")
    
    import subprocess
    import os
    
    # Crear entorno con ENV_FILE
    env = os.environ.copy()
    env['ENV_FILE'] = env_file
    
    cmd = (
        f"python -m src.predictions.cli betting-lines-validate "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )
    
    print_info(f"Usando configuración: {env_file}")
    result = subprocess.run(cmd, shell=True, env=env)
    
    if result.returncode == 0:
        print_success(f"Betting lines validadas para {league_config.league_name}")
        return True
    return False

def generate_best_bets(league_config: LeagueConfig, date_from: str, date_to: str, env_file: str, top_n: int = 4):
    """
    Genera las mejores apuestas para una liga específica.
    Llama al endpoint /api/best-bets/analysis-multiliga.
    """
    print_step(f"🎯 GENERANDO BEST BETS - {league_config.league_name}")
    
    try:
        
        # ✅ SWITCHEO SIMPLE: Por nombre exacto del archivo
        if env_file == ".env":  # LOCALHOST
            api_url = os.getenv('API_URL', 'http://localhost:8000')  # Con default
        else:  # PRODUCCIÓN (.env.production)
            api_url = os.getenv('API_URL')  # Sin default, DEBE estar definida
            if not api_url:
                print_error(f"API_URL no encontrada en {env_file}")
                return False

        
        # ✅ PASO 4: Mostrar configuración (debug)
        print_info(f"📁 Archivo config: {env_file}")
        print_info(f"🌐 API URL: {api_url}")
        
        # Preparar parámetros
        params = {
            'top_n': top_n,
            'min_confidence': 0.0  # Analizar todas, ordenar por score
        }
        
        # Agregar filtros de fecha si se especificaron
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to
        
        # Llamar al endpoint
        endpoint = f"{api_url}/api/best-bets/analysis-multiliga"
        print_info(f"Llamando a: {endpoint}")
        print_info(f"Parámetros: {params}")
        
        response = requests.get(endpoint, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'success':
                top_bets = result.get('top_bets', [])
                stats = result.get('statistics', {})
                
                print_success(f"✅ Best Bets generadas exitosamente")
                print_info(f"   • Total matches analizados: {stats.get('total_matches_analyzed', 0)}")
                print_info(f"   • Total recomendaciones: {stats.get('total_recommendations', 0)}")
                print_info(f"   • Top {top_n} guardadas en BD")
                
                # Mostrar resumen de las top bets
                if top_bets:
                    print(f"\n{Colors.BOLD}📊 TOP {len(top_bets)} APUESTAS:{Colors.END}")
                    for idx, bet in enumerate(top_bets, 1):
                        league_emoji = bet.get('league_emoji', '⚽')
                        print(f"   {idx}. {league_emoji} {bet['home_team']} vs {bet['away_team']}")
                        print(f"      {bet['bet_type']}: {bet['prediction']} | Score: {bet['combined_score']:.1f}")
                
                # Agrupar por tipo de apuesta
                by_type = stats.get('by_bet_type', {})
                if by_type:
                    print(f"\n{Colors.BOLD}📈 POR TIPO DE APUESTA:{Colors.END}")
                    for bet_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                        print(f"   • {bet_type}: {count} oportunidades")
                
                # Agrupar por liga
                by_league = stats.get('by_league', {})
                if by_league:
                    print(f"\n{Colors.BOLD}🏆 POR LIGA:{Colors.END}")
                    for league, count in sorted(by_league.items(), key=lambda x: x[1], reverse=True):
                        print(f"   • {league}: {count} apuestas")
                
                return True
            else:
                print_error(f"Error en respuesta: {result.get('message', 'Unknown error')}")
                return False
        else:
            print_error(f"Error HTTP {response.status_code}: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print_error("Timeout al llamar a la API (>30s)")
        return False
    except requests.exceptions.ConnectionError:
        print_error("No se pudo conectar a la API. ¿Está corriendo el servidor?")
        return False
    except Exception as e:
        print_error(f"Error generando best bets: {e}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# PASO 2: Agregar función de validación después de la anterior
# ============================================================================

def validate_best_bets(league_config: LeagueConfig, env_file: str):
    """
    Valida las best bets que ya tienen resultado.
    Actualiza hit, profit_loss, actual_result.
    """
    print_step(f"✅ VALIDANDO BEST BETS - {league_config.league_name}")
    
    try:

        # ✅ SWITCHEO SIMPLE: Por nombre exacto del archivo
        if env_file == ".env":  # LOCALHOST
            api_url = os.getenv('API_URL', 'http://localhost:8000')  # Con default
        else:  # PRODUCCIÓN (.env.production)
            api_url = os.getenv('API_URL')  # Sin default, DEBE estar definida
            if not api_url:
                print_error(f"API_URL no encontrada en {env_file}")
                return False
        
        # Llamar al endpoint de validación
        endpoint = f"{api_url}/api/best-bets/validate"
        params = {'season_id': league_config.season_id}
        
        print_info(f"Validando season_id: {league_config.season_id}")
        
        response = requests.post(endpoint, params=params, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('success'):
                validated = result.get('validated', 0)
                hits = result.get('hits', 0)
                misses = result.get('misses', 0)
                accuracy = result.get('accuracy', 0)
                
                print_success(f"✅ Validación completada")
                print_info(f"   • Apuestas validadas: {validated}")
                print_info(f"   • Aciertos: {hits}")
                print_info(f"   • Fallos: {misses}")
                print_info(f"   • Accuracy: {accuracy:.1f}%")
                
                return True
            else:
                print_warning("No hay best bets pendientes de validar")
                return True  # No es un error, simplemente no hay nada que validar
        else:
            print_error(f"Error HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Error validando best bets: {e}")
        return False
    
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCIÓN PRINCIPAL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 1: Seleccionar Base de Datos (NUEVO)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    db_name, env_file = select_database()
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 2: Seleccionar Liga(s) (ORIGINAL)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    with engine.begin() as conn:
        manager = LeagueManager(conn)
        selected_leagues = manager.select_leagues("Selecciona liga(s) a procesar")
        
        if not selected_leagues:
            print_error("No se seleccionaron ligas")
            return
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # RESTO DEL CÓDIGO ORIGINAL SIN CAMBIOS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    print("\n📋 Selecciona el modo de operación:\n")
    print("  1. 📥 FIXTURES - Cargar nuevos partidos desde CSV")
    print("  2. 🎯 PREDICT  - Generar predicciones para partidos sin resultados")
    print("  3. 📥 RESULTS  - Cargar resultados de partidos terminados")
    print("  4. 📊 EVALUATE - Evaluar predicciones vs resultados reales")
    print("  5. 🔄 RETRAIN  - Re-entrenar modelo Weinston")
    print("  6. 🚀 COMPLETE - Flujo completo nueva jornada")
    print("  7. 📊 FINISH   - Flujo completo post-partidos")
    print("  8. 🎯 BEST BETS - Generar mejores apuestas")
    print("  0. ❌ SALIR\n")
    
    choice = input(f"{Colors.GREEN}Selecciona una opción (0-7): {Colors.END}")
    
    if choice == "0":
        print_info("Saliendo...")
        return
    
    # Solicitar fechas
    date_from = None
    date_to = None
    
    if choice in ["2", "4", "6", "7"]:
        print(f"\n{Colors.BOLD}Rango de fechas:{Colors.END}")
        date_from = input("  Desde (YYYY-MM-DD): ").strip()
        date_to = input("  Hasta (YYYY-MM-DD): ").strip()
        
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            print_error("Formato de fecha inválido")
            return
    
    # Confirmar operación
    mode_names = {
        "1": "CARGAR FIXTURES",
        "2": "GENERAR PREDICCIONES",
        "3": "CARGAR RESULTADOS",
        "4": "EVALUAR PREDICCIONES",
        "5": "RE-ENTRENAR WEINSTON",
        "6": "FLUJO COMPLETO PRE-PARTIDOS",
        "7": "FLUJO COMPLETO POST-PARTIDOS",
        "8": "GENERAR MEJORES APUESTAS"
    }
    
    operation_name = mode_names.get(choice, "OPERACIÓN")
    
    print(f"\n{Colors.YELLOW}{'─'*70}{Colors.END}")
    print(f"{Colors.BOLD}Confirmar operación:{Colors.END}")
    print(f"  • Base de datos: {db_name}")
    print(f"  • Operación: {operation_name}")
    print(f"  • Ligas: {', '.join([lc.league_name for lc in selected_leagues])}")
    print(f"{Colors.YELLOW}{'─'*70}{Colors.END}\n")
    
    response = input(f"{Colors.GREEN}¿Continuar? (s/n): {Colors.END}")
    
    if response.lower() != 's':
        print_info("Operación cancelada")
        return
    
    # Ejecutar para cada liga
    success_count = 0
    failed_leagues = []
    
    try:
        for idx, league_config in enumerate(selected_leagues, 1):
            print_league_header(league_config, idx, len(selected_leagues))
            
            success = False
            
            try:
                if choice == "1":
                    success = mode_load_fixtures(league_config, env_file)
                
                elif choice == "2":
                    success = mode_predict(league_config, date_from, date_to)
                
                elif choice == "3":
                    success = mode_load_results(league_config, env_file)
                
                elif choice == "4":
                    success = mode_evaluate(league_config, date_from, date_to, env_file)
                
                elif choice == "5":
                    success = mode_retrain(league_config, env_file)
                
                elif choice == "6":
                    # Flujo COMPLETE
                    print_info("Flujo: FIXTURES → RETRAIN → PREDICT → BETTING LINES → BEST BETS")
                    
                    if mode_load_fixtures(league_config, env_file):
                        if mode_retrain(league_config, env_file):
                            if mode_predict(league_config, date_from, date_to):
                                if generate_betting_lines_predictions(league_config, date_from, date_to, env_file):
                                    generate_best_bets(league_config, date_from, date_to, env_file, top_n=4)
                                    success = True
                
                elif choice == "7":
                    # Flujo FINISH
                    print_info("Flujo: RESULTS → EVALUATE → VALIDATE BETTING → VALIDATE BEST BETS")
                    
                    if mode_load_results(league_config, env_file):
                        if mode_evaluate(league_config, date_from, date_to, env_file):
                            if validate_betting_lines_predictions(league_config, date_from, date_to, env_file):
                                validate_best_bets(league_config, env_file)
                                success = True

                elif choice == "8":
                    # Solo best bets
                    print_info("Generando Best Bets para todas las ligas...")
                    
                    # Generar para cada liga seleccionada
                    for league_config in selected_leagues:
                        print(f"\n{Colors.BOLD}{league_config.league_name}{Colors.END}")
                        if generate_best_bets(league_config, date_from, date_to, env_file, top_n=4):
                            print_success(f"✓ {league_config.league_name}")
                            success = True
                        else:
                            print_warning(f"⚠️  {league_config.league_name}")
                            success = False
                
                else:
                    print_error("Opción inválida")
                    return
                
                if success:
                    print_success(f"✓ {league_config.league_name} completada exitosamente")
                    success_count += 1
                else:
                    print_warning(f"⚠️  {league_config.league_name} completada con advertencias")
                    failed_leagues.append(league_config.league_name)
                    
            except Exception as e:
                print_error(f"Error en {league_config.league_name}: {e}")
                failed_leagues.append(league_config.league_name)
                continue
        
        # Resumen final
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}  RESUMEN DE OPERACIÓN{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
        
        print(f"  Base de datos: {Colors.BOLD}{db_name}{Colors.END}")
        print(f"  Ligas procesadas: {success_count}/{len(selected_leagues)}")
        
        if success_count == len(selected_leagues):
            print_success("✅ Todas las ligas se procesaron exitosamente")
        elif success_count > 0:
            print_warning(f"⚠️  {len(failed_leagues)} liga(s) tuvieron problemas:")
            for league_name in failed_leagues:
                print(f"     • {league_name}")
        else:
            print_error("❌ No se pudo procesar ninguna liga")
        
        print()
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Operación cancelada por el usuario{Colors.END}")
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()