#!/usr/bin/env python
"""
Script inteligente para actualizar predicciones - VERSIÓN MULTI-LIGA.
Valida el estado del sistema antes de ejecutar comandos.

CAMBIOS PRINCIPALES:
- Soporte para múltiples ligas simultáneas
- Usa LeagueContext para independencia entre ligas
- Llamadas directas a funciones (sin subprocess)
- Mensajes más claros indicando la liga procesada
"""
import sys
from datetime import datetime
from typing import Tuple, Optional, List
from sqlalchemy import text
from src.db import engine

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
# FUNCIONES DE VERIFICACIÓN (sin cambios, solo documentadas)
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
# MODOS REFACTORIZADOS (con soporte multi-liga)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def mode_load_fixtures(league_config: LeagueConfig):
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
        print_info("Operación cancelada")
        return False
    
    # 5. Ejecutar carga
    import subprocess
    
    cmd = (
        f"python -m src.fixtures.cli bulk {filepath} "
        f"--season-id {league_config.season_id} "
        f"--league \"{league_config.league_name}\" "
    )
    
    if league_config.dayfirst:
        cmd += "--dayfirst"
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print_success(f"Fixtures cargados exitosamente para {league_config.league_name}")
        return True
    else:
        print_error("Error al cargar fixtures")
        return False


def mode_predict(league_config: LeagueConfig, date_from: str, date_to: str):
    """Modo: Generar predicciones para partidos futuros de una liga"""
    print_step(f"🎯 MODO: GENERAR PREDICCIONES - {league_config.league_name}")
    
    season_id = league_config.season_id
    
    # 1. Verificar partidos sin resultados
    count, matches = check_matches_without_results(season_id, date_from, date_to)
    
    if count == 0:
        print_warning(f"No hay partidos sin resultados para {league_config.league_name}")
        return False
    
    print_success(f"Hay {count} partidos sin resultados")
    
    # 2. Verificar predicciones existentes
    match_ids = [m.id for m in matches]
    existing = check_predictions_exist(match_ids)
    
    if existing["poisson"] > 0 or existing["weinston"] > 0:
        print_warning(f"Algunos partidos ya tienen predicciones:")
        print(f"   • Poisson: {existing['poisson']}/{count}")
        print(f"   • Weinston: {existing['weinston']}/{count}")
        print_info("Las predicciones se actualizarán")
        
        response = input(f"\n{Colors.YELLOW}¿Continuar? (s/n): {Colors.END}")
        if response.lower() != 's':
            return False
    
    # 3. Cargar contexto de liga y generar predicciones
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


def mode_load_results(league_config: LeagueConfig):
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
    
    # 5. Ejecutar carga
    import subprocess
    
    cmd = (
        f"python -m src.ingest.load_unified {filepath} "
        f"--league \"{league_config.league_name}\" "
        f"--div {league_config.csv_code} "
        f"--season-id {league_config.season_id} "
    )
    
    if league_config.dayfirst:
        cmd += "--dayfirst"
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print_success(f"Resultados cargados para {league_config.league_name}")
        return True
    else:
        print_error("Error al cargar resultados")
        return False


def mode_evaluate(league_config: LeagueConfig, date_from: str, date_to: str):
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
    
    # 4. Ejecutar evaluación
    import subprocess
    
    cmd = (
        f"python -m src.predictions.cli evaluate "
        f"--season-id {season_id} "
        f"--from {date_from} --to {date_to}"
    )
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print_success(f"Evaluación completada para {league_config.league_name}")
        return True
    else:
        print_error("Error al evaluar predicciones")
        return False


def mode_retrain(league_config: LeagueConfig):
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
    else:
        print_success(f"Hay {total_matches} partidos terminados disponibles")
    
    # 2. Verificar parámetros actuales
    params = check_weinston_params(season_id)
    if params:
        print_info(f"Parámetros actuales (desde {params['updated_at']}):")
        print(f"   μ_home={params['mu_home']:.3f}, μ_away={params['mu_away']:.3f}, HFA={params['home_adv']:.3f}")
    else:
        print_info("No hay parámetros previos, primer entrenamiento")
    
    # 3. Confirmar
    response = input(f"\n{Colors.GREEN}¿Re-entrenar modelo? (s/n): {Colors.END}")
    if response.lower() != 's':
        return False
    
    # 4. Entrenar
    import subprocess
    
    cmd = f"python -m src.predictions.cli fit --season-id {season_id}"
    
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print_success(f"Modelo re-entrenado para {league_config.league_name}")
        return True
    else:
        print_error("Error al entrenar modelo")
        return False


def generate_betting_lines_predictions(league_config: LeagueConfig, date_from: str, date_to: str):
    """Genera líneas de apuesta para una liga"""
    print_info(f"Generando betting lines para {league_config.league_name}...")
    
    import subprocess
    
    cmd = (
        f"python -m src.predictions.cli betting-lines "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print_success(f"Betting lines generadas para {league_config.league_name}")
        return True
    return False


def validate_betting_lines_predictions(league_config: LeagueConfig, date_from: str, date_to: str):
    """Valida líneas de apuesta contra resultados reales"""
    print_info(f"Validando betting lines para {league_config.league_name}...")
    
    import subprocess
    
    cmd = (
        f"python -m src.predictions.cli betting-lines-validate "
        f"--season-id {league_config.season_id} "
        f"--from {date_from} --to {date_to}"
    )
    
    result = subprocess.run(cmd, shell=True)
    
    if result.returncode == 0:
        print_success(f"Betting lines validadas para {league_config.league_name}")
        return True
    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FUNCIÓN PRINCIPAL (MULTI-LIGA)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     55sportsBet - Actualización Inteligente MULTI-LIGA    ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 1: Seleccionar Liga(s)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    with engine.begin() as conn:
        manager = LeagueManager(conn)
        selected_leagues = manager.select_leagues("Selecciona liga(s) a procesar")
        
        if not selected_leagues:
            print_error("No se seleccionaron ligas")
            return
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 2: Seleccionar Modo de Operación
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    print("\n📋 Selecciona el modo de operación:\n")
    print("  1. 📥 FIXTURES - Cargar nuevos partidos desde CSV")
    print("  2. 🎯 PREDICT  - Generar predicciones para partidos sin resultados")
    print("  3. 📥 RESULTS  - Cargar resultados de partidos terminados")
    print("  4. 📊 EVALUATE - Evaluar predicciones vs resultados reales")
    print("  5. 🔄 RETRAIN  - Re-entrenar modelo Weinston")
    print("  6. 🚀 COMPLETE - Flujo completo nueva jornada")
    print("  7. 📊 FINISH   - Flujo completo post-partidos")
    print("  0. ❌ SALIR\n")
    
    choice = input(f"{Colors.GREEN}Selecciona una opción (0-7): {Colors.END}")
    
    if choice == "0":
        print_info("Saliendo...")
        return
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 3: Solicitar Fechas (si es necesario)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
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
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 4: Confirmar Operación Multi-Liga
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    mode_names = {
        "1": "CARGAR FIXTURES",
        "2": "GENERAR PREDICCIONES",
        "3": "CARGAR RESULTADOS",
        "4": "EVALUAR PREDICCIONES",
        "5": "RE-ENTRENAR WEINSTON",
        "6": "FLUJO COMPLETO PRE-PARTIDOS",
        "7": "FLUJO COMPLETO POST-PARTIDOS"
    }
    
    operation_name = mode_names.get(choice, "OPERACIÓN")
    
    if not manager.confirm_multi_league_operation(selected_leagues, operation_name):
        print_info("Operación cancelada")
        return
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # PASO 5: Ejecutar para cada liga
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    success_count = 0
    failed_leagues = []
    
    try:
        for idx, league_config in enumerate(selected_leagues, 1):
            print_league_header(league_config, idx, len(selected_leagues))
            
            success = False
            
            try:
                if choice == "1":
                    success = mode_load_fixtures(league_config)
                
                elif choice == "2":
                    success = mode_predict(league_config, date_from, date_to)
                
                elif choice == "3":
                    success = mode_load_results(league_config)
                
                elif choice == "4":
                    success = mode_evaluate(league_config, date_from, date_to)
                
                elif choice == "5":
                    success = mode_retrain(league_config)
                
                elif choice == "6":
                    # Flujo COMPLETE
                    print_info("Flujo: FIXTURES → RETRAIN → PREDICT → BETTING LINES")
                    
                    if mode_load_fixtures(league_config):
                        if mode_retrain(league_config):
                            if mode_predict(league_config, date_from, date_to):
                                generate_betting_lines_predictions(league_config, date_from, date_to)
                                success = True
                
                elif choice == "7":
                    # Flujo FINISH
                    print_info("Flujo: RESULTS → EVALUATE → VALIDATE BETTING")
                    
                    if mode_load_results(league_config):
                        if mode_evaluate(league_config, date_from, date_to):
                            validate_betting_lines_predictions(league_config, date_from, date_to)
                            success = True
                
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
        
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        # RESUMEN FINAL
        # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}  RESUMEN DE OPERACIÓN{Colors.END}")
        print(f"{Colors.CYAN}{'='*70}{Colors.END}\n")
        
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