#!/usr/bin/env python
"""
Script inteligente para actualizar predicciones.
Valida el estado del sistema antes de ejecutar comandos.
"""
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Tuple, Optional
from sqlalchemy import text
from src.db import engine

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    END = '\033[0m'
    BOLD = '\033[1m'

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

def run_command(cmd: str) -> bool:
    """Ejecuta comando y retorna True si tuvo éxito"""
    print(f"\n{Colors.CYAN}🔄 Ejecutando: {cmd}{Colors.END}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode == 0:
        print_success("Comando completado")
        return True
    else:
        print_error("Comando falló")
        return False

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

def mode_load_fixtures(season_id: int, league: str = "Premier League", dayfirst: bool = True):
    """Modo: Cargar fixtures desde CSV"""
    print_step("📥 MODO: CARGAR FIXTURES")
    
    # 1. Solicitar ruta del archivo
    print_info("Ingresa la ruta del archivo CSV con los fixtures")
    print_info("Ejemplo: data/fixtures_E0.csv")
    
    filepath = input(f"\n{Colors.GREEN}Ruta del archivo: {Colors.END}").strip()
    
    if not filepath:
        print_error("Ruta vacía")
        return False
    
    # 2. Verificar que existe
    if not check_fixtures_file(filepath):
        return False
    
    # 3. Preview del contenido
    total_rows = preview_csv_fixtures(filepath)
    
    if total_rows == 0:
        print_error("No se pudieron leer filas del CSV")
        return False
    
    # 4. Verificar fixtures ya cargados
    print_info("\nVerificando fixtures existentes en la base de datos...")
    query = text("""
        SELECT COUNT(*) as total,
               COUNT(*) FILTER (WHERE home_goals IS NULL) as sin_resultados,
               COUNT(*) FILTER (WHERE home_goals IS NOT NULL) as con_resultados
        FROM matches
        WHERE season_id = :sid
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query, {"sid": season_id}).fetchone()
        total_existing = row.total
        sin_res = row.sin_resultados
        con_res = row.con_resultados
    
    if total_existing > 0:
        print_warning(f"Ya hay {total_existing} partidos en la BD para season {season_id}")
        print(f"   • Sin resultados: {sin_res}")
        print(f"   • Con resultados: {con_res}")
        print_warning("Los partidos duplicados se actualizarán")
    else:
        print_success("No hay fixtures previos, esta será la primera carga")
    
    # 5. Confirmar parámetros
    print(f"\n{Colors.BOLD}Resumen:{Colors.END}")
    print(f"  • Archivo: {filepath}")
    print(f"  • Season ID: {season_id}")
    print(f"  • Liga: {league}")
    print(f"  • Formato fecha: {'DD/MM/YYYY' if dayfirst else 'MM/DD/YYYY'}")
    print(f"  • Partidos a cargar: {total_rows}")
    
    response = input(f"\n{Colors.GREEN}¿Proceder con la carga de fixtures? (s/n): {Colors.END}")
    if response.lower() != 's':
        print_info("Operación cancelada")
        return False
    
    # 6. Ejecutar carga
    cmd = f'python -m src.fixtures.cli bulk "{filepath}" --season-id {season_id} --league "{league}"'
    if dayfirst:
        cmd += " --dayfirst"
    
    if not run_command(cmd):
        return False
    
    # 7. Verificar resultado
    print_info("\nVerificando fixtures cargados...")
    with engine.begin() as conn:
        row = conn.execute(query, {"sid": season_id}).fetchone()
        new_total = row.total
        new_sin_res = row.sin_resultados
    
    print_success(f"¡Fixtures cargados exitosamente!")
    print(f"   • Total partidos en BD: {new_total}")
    print(f"   • Sin resultados (listos para predecir): {new_sin_res}")
    
    print_info("💡 Próximo paso: Genera predicciones con el modo 'PREDICT'")
    return True

def mode_predict(season_id: int, date_from: str, date_to: str):
    """Modo: Generar predicciones para partidos sin resultados"""
    print_step("🎯 MODO: GENERAR PREDICCIONES")
    
    # 1. Verificar partidos sin resultados
    print_info("Verificando partidos sin resultados...")
    count, matches = check_matches_without_results(season_id, date_from, date_to)
    
    if count == 0:
        print_error(f"No hay partidos sin resultados entre {date_from} y {date_to}")
        print_info("💡 Tip: Verifica que hayas cargado los fixtures con el comando bulk")
        return False
    
    print_success(f"Encontrados {count} partidos sin resultados")
    
    # Mostrar partidos
    print("\n📋 Partidos a predecir:")
    for m in matches[:5]:  # Mostrar máximo 5
        print(f"   • Match ID {m.id} - {m.date}")
    if len(matches) > 5:
        print(f"   ... y {len(matches) - 5} más")
    
    # 2. Verificar predicciones existentes
    match_ids = [m.id for m in matches]
    pred_counts = check_predictions_exist(match_ids)
    
    if pred_counts["poisson"] > 0 or pred_counts["weinston"] > 0:
        print_warning(f"Ya existen predicciones: Poisson={pred_counts['poisson']}, Weinston={pred_counts['weinston']}")
        print_info("Se sobrescribirán las predicciones existentes")
    
    # 3. Verificar parámetros de Weinston
    print_info("Verificando parámetros de Weinston...")
    params = check_weinston_params(season_id)
    
    if params:
        print_success(f"Parámetros Weinston encontrados (actualizado: {params['updated_at']})")
        print(f"   μ_home={params['mu_home']:.3f}, μ_away={params['mu_away']:.3f}, HFA={params['home_adv']:.3f}")
    else:
        print_warning("No hay parámetros Weinston para esta temporada")
        response = input(f"\n{Colors.YELLOW}¿Deseas entrenar el modelo ahora? (s/n): {Colors.END}")
        if response.lower() == 's':
            if not run_command(f"python -m src.predictions.cli fit --season-id {season_id}"):
                return False
        else:
            print_warning("Continuando con valores de fallback (menos preciso)")
    
    # 4. Confirmar ejecución
    print(f"\n{Colors.BOLD}Resumen:{Colors.END}")
    print(f"  • Season ID: {season_id}")
    print(f"  • Rango: {date_from} a {date_to}")
    print(f"  • Partidos a predecir: {count}")
    
    response = input(f"\n{Colors.GREEN}¿Proceder con la generación de predicciones? (s/n): {Colors.END}")
    if response.lower() != 's':
        print_info("Operación cancelada")
        return False
    
    # 5. Generar predicciones
    if not run_command(f"python -m src.predictions.cli upcoming --season-id {season_id} --from {date_from} --to {date_to}"):
        return False
    
    print_success("¡Predicciones generadas exitosamente!")
    print_info("💡 Próximo paso: Esperar resultados y ejecutar el modo 'evaluate'")
    return True

def mode_load_results(season_id: int, league: str = "Premier League", div: str = "E0", dayfirst: bool = True):
    """Modo: Cargar resultados desde CSV"""
    print_step("📥 MODO: CARGAR RESULTADOS")
    
    # 1. Solicitar ruta del archivo
    print_info("Ingresa la ruta del archivo CSV con los resultados")
    print_info("Ejemplo: data/raw/E0.csv")
    
    filepath = input(f"\n{Colors.GREEN}Ruta del archivo: {Colors.END}").strip()
    
    if not filepath:
        print_error("Ruta vacía")
        return False
    
    # 2. Verificar que existe
    if not check_fixtures_file(filepath):
        return False
    
    # 3. Preview del contenido
    print_info("\nAnalizando archivo CSV...")
    try:
        import csv
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        # Contar partidos con resultados
        with_results = [r for r in rows if r.get('FTR') and r.get('FTHG') and r.get('FTAG')]
        
        print(f"\n📋 Contenido del CSV:")
        print(f"   • Total filas: {len(rows)}")
        print(f"   • Con resultados (FTR/FTHG/FTAG): {len(with_results)}")
        
        if with_results:
            print(f"\n   Últimos 5 resultados:")
            for i, row in enumerate(with_results[-5:], 1):
                date = row.get('Date', 'N/A')
                home = row.get('HomeTeam', 'N/A')
                away = row.get('AwayTeam', 'N/A')
                fthg = row.get('FTHG', '?')
                ftag = row.get('FTAG', '?')
                print(f"     {i}. {date}: {home} {fthg}-{ftag} {away}")
    
    except Exception as e:
        print_error(f"Error al leer CSV: {e}")
        return False
    
    # 4. Verificar partidos sin resultados en BD
    print_info("\nVerificando partidos sin resultados en la base de datos...")
    query = text("""
        SELECT COUNT(*) as total_sin_resultados,
               MIN(date) as fecha_min,
               MAX(date) as fecha_max
        FROM matches
        WHERE season_id = :sid
          AND home_goals IS NULL
          AND away_goals IS NULL
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query, {"sid": season_id}).fetchone()
        sin_resultados = row.total_sin_resultados or 0
        fecha_min = row.fecha_min
        fecha_max = row.fecha_max
    
    if sin_resultados == 0:
        print_warning("No hay partidos sin resultados en la BD")
        print_info("Esto puede significar que ya cargaste los resultados antes")
    else:
        print_success(f"Hay {sin_resultados} partidos sin resultados esperando actualización")
        if fecha_min and fecha_max:
            print(f"   Rango de fechas: {fecha_min} a {fecha_max}")
    
    # 5. Advertencia sobre partidos con predicciones
    query_pred = text("""
        SELECT COUNT(DISTINCT m.id) as con_predicciones
        FROM matches m
        WHERE m.season_id = :sid
          AND m.home_goals IS NULL
          AND (EXISTS (SELECT 1 FROM poisson_predictions WHERE match_id = m.id)
               OR EXISTS (SELECT 1 FROM weinston_predictions WHERE match_id = m.id))
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query_pred, {"sid": season_id}).fetchone()
        con_pred = row.con_predicciones or 0
    
    if con_pred > 0:
        print_warning(f"Hay {con_pred} partidos con predicciones que recibirán resultados")
        print_info("Después de cargar, recuerda ejecutar EVALUATE para calcular aciertos")
    
    # 6. Confirmar parámetros
    print(f"\n{Colors.BOLD}Resumen:{Colors.END}")
    print(f"  • Archivo: {filepath}")
    print(f"  • Season ID: {season_id}")
    print(f"  • Liga: {league}")
    print(f"  • División: {div}")
    print(f"  • Formato fecha: {'DD/MM/YYYY' if dayfirst else 'MM/DD/YYYY'}")
    print(f"  • Resultados en CSV: {len(with_results)}")
    print(f"  • Partidos sin resultados en BD: {sin_resultados}")
    
    response = input(f"\n{Colors.GREEN}¿Proceder con la carga de resultados? (s/n): {Colors.END}")
    if response.lower() != 's':
        print_info("Operación cancelada")
        return False
    
    # 7. Ejecutar carga
    cmd = f'python -m src.ingest.load_unified "{filepath}" --league "{league}" --div {div} --season-id {season_id}'
    if dayfirst:
        cmd += " --dayfirst"
    
    if not run_command(cmd):
        return False
    
    # 8. Verificar resultado
    print_info("\nVerificando resultados cargados...")
    query_after = text("""
        SELECT 
            COUNT(*) FILTER (WHERE home_goals IS NULL) as sin_resultados,
            COUNT(*) FILTER (WHERE home_goals IS NOT NULL) as con_resultados
        FROM matches
        WHERE season_id = :sid
    """)
    
    with engine.begin() as conn:
        row = conn.execute(query_after, {"sid": season_id}).fetchone()
        nuevos_sin = row.sin_resultados or 0
        nuevos_con = row.con_resultados or 0
    
    partidos_actualizados = sin_resultados - nuevos_sin
    
    print_success(f"¡Resultados cargados exitosamente!")
    print(f"   • Partidos actualizados: {partidos_actualizados}")
    print(f"   • Total con resultados: {nuevos_con}")
    print(f"   • Aún sin resultados: {nuevos_sin}")
    
    if con_pred > 0:
        print_info(f"\n💡 Próximo paso: Ejecuta el modo EVALUATE para calcular aciertos")
        print_info(f"   de los {con_pred} partidos con predicciones")
    
    return True

def mode_evaluate(season_id: int, date_from: str, date_to: str):
    """Modo: Evaluar predicciones de partidos terminados"""
    print_step("📊 MODO: EVALUAR PREDICCIONES")
    
    # 1. Verificar partidos CON resultados
    print_info("Verificando partidos con resultados...")
    count, matches = check_matches_with_results(season_id, date_from, date_to)
    
    if count == 0:
        print_error(f"No hay partidos con resultados entre {date_from} y {date_to}")
        print_info("💡 Tip: Ejecuta primero 'python -m src.ingest.load_unified' para cargar resultados")
        return False
    
    print_success(f"Encontrados {count} partidos con resultados")
    
    # 2. Verificar que existan predicciones
    match_ids = [m.id for m in matches]
    pred_counts = check_predictions_exist(match_ids)
    
    if pred_counts["poisson"] == 0 and pred_counts["weinston"] == 0:
        print_error("No existen predicciones para estos partidos")
        print_info("💡 Ejecuta primero el modo 'predict' para generar predicciones")
        return False
    
    print_success(f"Predicciones encontradas: Poisson={pred_counts['poisson']}, Weinston={pred_counts['weinston']}")
    
    # 3. Verificar evaluaciones existentes
    eval_counts = check_evaluated_matches(season_id, date_from, date_to)
    if eval_counts["poisson"] > 0 or eval_counts["weinston"] > 0:
        print_warning(f"Ya hay evaluaciones: Poisson={eval_counts['poisson']}, Weinston={eval_counts['weinston']}")
        print_info("Se actualizarán las evaluaciones existentes")
    
    # 4. Confirmar ejecución
    print(f"\n{Colors.BOLD}Resumen:{Colors.END}")
    print(f"  • Season ID: {season_id}")
    print(f"  • Rango: {date_from} a {date_to}")
    print(f"  • Partidos a evaluar: {count}")
    
    response = input(f"\n{Colors.GREEN}¿Proceder con la evaluación? (s/n): {Colors.END}")
    if response.lower() != 's':
        print_info("Operación cancelada")
        return False
    
    # 5. Calcular RMSE de Weinston
    print_info("Calculando RMSE de Weinston...")
    if not run_command(f"python -m src.predictions.cli score --season-id {season_id} --from {date_from} --to {date_to} --metric rmse"):
        print_warning("Error al calcular RMSE, continuando...")
    
    # 6. Evaluar predicciones
    if not run_command(f"python -m src.predictions.cli evaluate --season-id {season_id} --from {date_from} --to {date_to}"):
        return False
    
    print_success("¡Evaluación completada exitosamente!")
    print_info("💡 Puedes ver los resultados en el frontend")
    return True

def mode_retrain(season_id: int):
    """Modo: Re-entrenar modelo Weinston"""
    print_step("🔄 MODO: RE-ENTRENAR WEINSTON")
    
    # 1. Verificar cuántos partidos terminados hay
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
        print_warning(f"Solo hay {total_matches} partidos terminados")
        print_warning("Se recomienda al menos 10 partidos para entrenar el modelo")
        response = input(f"\n{Colors.YELLOW}¿Continuar de todos modos? (s/n): {Colors.END}")
        if response.lower() != 's':
            return False
    else:
        print_success(f"Hay {total_matches} partidos terminados disponibles para entrenamiento")
    
    # 2. Verificar parámetros actuales
    params = check_weinston_params(season_id)
    if params:
        print_info(f"Parámetros actuales (desde {params['updated_at']}):")
        print(f"   μ_home={params['mu_home']:.3f}, μ_away={params['mu_away']:.3f}, HFA={params['home_adv']:.3f}, loss={params['loss']:.2f}")
    else:
        print_info("No hay parámetros previos, este será el primer entrenamiento")
    
    # 3. Confirmar
    response = input(f"\n{Colors.GREEN}¿Re-entrenar el modelo Weinston? (s/n): {Colors.END}")
    if response.lower() != 's':
        print_info("Operación cancelada")
        return False
    
    # 4. Entrenar
    if not run_command(f"python -m src.predictions.cli fit --season-id {season_id}"):
        return False
    
    print_success("¡Modelo re-entrenado exitosamente!")
    print_info("💡 Ahora puedes generar nuevas predicciones con el modelo actualizado")
    return True

def main():
    print(f"{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        55sportsBet - Actualización Inteligente            ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    # Configuración
    season_id = 2
    
    # Selección de modo
    print("\n📋 Selecciona el modo de operación:\n")
    print("  1. 📥 FIXTURES - Cargar nuevos partidos desde CSV (sin resultados)")
    print("  2. 🎯 PREDICT  - Generar predicciones para partidos sin resultados")
    print("  3. 📥 RESULTS  - Cargar resultados de partidos terminados desde CSV")
    print("  4. 📊 EVALUATE - Evaluar predicciones vs resultados reales")
    print("  5. 🔄 RETRAIN  - Re-entrenar modelo Weinston con nuevos datos")
    print("  6. 🚀 COMPLETE - Flujo completo nueva jornada (fixtures + retrain + predict)")
    print("  7. 📊 FINISH   - Flujo completo post-partidos (results + evaluate)")
    print("  0. ❌ SALIR\n")
    
    choice = input(f"{Colors.GREEN}Selecciona una opción (0-7): {Colors.END}")
    
    if choice == "0":
        print_info("Saliendo...")
        return
    
    # Solicitar fechas si es necesario
    date_from = None
    date_to = None
    
    if choice in ["2", "4", "6", "7"]:
        print(f"\n{Colors.BOLD}Rango de fechas:{Colors.END}")
        date_from = input("  Desde (YYYY-MM-DD): ").strip()
        date_to = input("  Hasta (YYYY-MM-DD): ").strip()
        
        # Validar formato de fecha
        try:
            datetime.strptime(date_from, "%Y-%m-%d")
            datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            print_error("Formato de fecha inválido. Usa YYYY-MM-DD")
            return
    
    # Ejecutar modo seleccionado
    try:
        if choice == "1":
            mode_load_fixtures(season_id)
        elif choice == "2":
            mode_predict(season_id, date_from, date_to)
        elif choice == "3":
            mode_load_results(season_id)
        elif choice == "4":
            mode_evaluate(season_id, date_from, date_to)
        elif choice == "5":
            mode_retrain(season_id)
        elif choice == "6":
            # Flujo completo: ANTES de los partidos
            print_step("🚀 FLUJO COMPLETO: NUEVA JORNADA (PRE-PARTIDOS)")
            print_info("Este proceso ejecutará: FIXTURES → RETRAIN → PREDICT")
            
            # Paso 1: Cargar fixtures
            if not mode_load_fixtures(season_id):
                print_error("Fallo al cargar fixtures, abortando flujo")
                return
            
            input(f"\n{Colors.YELLOW}✓ Fixtures cargados. Presiona Enter para continuar con RETRAIN...{Colors.END}")
            
            # Paso 2: Re-entrenar Weinston
            if not mode_retrain(season_id):
                print_error("Fallo al entrenar modelo, abortando flujo")
                return
            
            input(f"\n{Colors.YELLOW}✓ Modelo entrenado. Presiona Enter para continuar con PREDICT...{Colors.END}")
            
            # Paso 3: Generar predicciones
            if mode_predict(season_id, date_from, date_to):
                print(f"\n{Colors.GREEN}{Colors.BOLD}")
                print("╔════════════════════════════════════════════════════════════╗")
                print("║          ✅ FLUJO PRE-PARTIDOS COMPLETADO ✅             ║")
                print("╚════════════════════════════════════════════════════════════╝")
                print(f"{Colors.END}")
                print_info("💡 Los partidos están listos con predicciones")
                print_info("⚽ Ahora espera a que se jueguen los partidos")
                print_info("📊 Después ejecuta el modo 7 (FINISH) para cargar resultados y evaluar")
        
        elif choice == "7":
            # Flujo completo: DESPUÉS de los partidos
            print_step("📊 FLUJO COMPLETO: POST-PARTIDOS (RESULTS + EVALUATE)")
            print_info("Este proceso ejecutará: RESULTS → EVALUATE")
            
            # Paso 1: Cargar resultados
            if not mode_load_results(season_id):
                print_error("Fallo al cargar resultados, abortando flujo")
                return
            
            input(f"\n{Colors.YELLOW}✓ Resultados cargados. Presiona Enter para continuar con EVALUATE...{Colors.END}")
            
            # Paso 2: Evaluar predicciones
            if mode_evaluate(season_id, date_from, date_to):
                print(f"\n{Colors.GREEN}{Colors.BOLD}")
                print("╔════════════════════════════════════════════════════════════╗")
                print("║         ✅ FLUJO POST-PARTIDOS COMPLETADO ✅             ║")
                print("╚════════════════════════════════════════════════════════════╝")
                print(f"{Colors.END}")
                print_info("💡 Predicciones evaluadas y métricas actualizadas")
                print_info("🖥️  Puedes ver los resultados en el frontend")
                print_info("🔄 Para la siguiente jornada, ejecuta el modo 6 (COMPLETE)")
        else:
            print_error("Opción inválida")
    
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Operación cancelada por el usuario{Colors.END}")
    except Exception as e:
        print_error(f"Error inesperado: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()