#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_best_bets.py
=================
Sincroniza best_bets_history de PRODUCCIÓN a LOCALHOST
Usa la misma lógica de conexión que update_predictions.py
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

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


def create_engine_from_env(env_file: str, db_name: str):
    """
    Crea engine usando la MISMA lógica que update_predictions.py
    """
    # Verificar que el archivo existe
    if not os.path.exists(env_file):
        print_error(f"Archivo no encontrado: {env_file}")
        print_info(f"Ruta esperada: {os.path.abspath(env_file)}")
        return None
    
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
        return None
    
    # Construir URL de conexión
    database_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_database}"
    
    # Crear engine
    try:
        engine = create_engine(database_url)
        
        # Probar conexión
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        print_success(f"Conectado a {db_name}: {db_database}")
        return engine
        
    except Exception as e:
        print_error(f"Error al conectar a {db_name}")
        print(f"{Colors.RED}Detalles: {str(e)}{Colors.END}")
        return None


def connect_databases():
    """Conecta a ambas bases de datos usando la lógica del proyecto"""
    
    print_title("🔌 CONECTANDO A BASES DE DATOS")
    
    # PRODUCCIÓN
    engine_prod = create_engine_from_env('.env.production', 'PRODUCCIÓN')
    if not engine_prod:
        return None, None
    
    # LOCALHOST
    engine_local = create_engine_from_env('.env', 'LOCALHOST')
    if not engine_local:
        return None, None
    
    return engine_prod, engine_local


def get_best_bets_from_production(engine_prod):
    """Obtiene todos los best_bets de producción"""
    
    print_title("📥 EXTRAYENDO BEST BETS DE PRODUCCIÓN")
    
    query = text("""
        SELECT 
            bbh.id as prod_id,
            bbh.match_id as prod_match_id,
            bbh.season_id,
            bbh.date,
            bbh.home_team,
            bbh.away_team,
            bbh.model,
            bbh.bet_type,
            bbh.prediction,
            bbh.confidence,
            bbh.historical_accuracy,
            bbh.combined_score,
            bbh.rank,
            bbh.odds,
            bbh.created_at,
            bbh.validated_at,
            bbh.hit,
            bbh.profit_loss,
            bbh.actual_result
        FROM best_bets_history bbh
        ORDER BY bbh.date DESC, bbh.created_at DESC
    """)
    
    with engine_prod.connect() as conn:
        results = conn.execute(query).mappings().all()
    
    print_info(f"Total de registros en PRODUCCIÓN: {len(results)}")
    
    return results


def get_existing_bets_from_localhost(engine_local):
    """Obtiene los best_bets existentes en localhost"""
    
    print_title("📋 VERIFICANDO BEST BETS EN LOCALHOST")
    
    query = text("""
        SELECT 
            bbh.date,
            bbh.home_team,
            bbh.away_team,
            bbh.model,
            bbh.bet_type
        FROM best_bets_history bbh
    """)
    
    with engine_local.connect() as conn:
        results = conn.execute(query).mappings().all()
    
    # Crear set de claves compuestas
    existing_keys = set()
    for row in results:
        key = (
            row['date'].strftime('%Y-%m-%d') if row['date'] else None,
            row['home_team'],
            row['away_team'],
            row['model'],
            row['bet_type']
        )
        existing_keys.add(key)
    
    print_info(f"Total de registros en LOCALHOST: {len(existing_keys)}")
    
    return existing_keys


def find_match_id_in_localhost(engine_local, date, home_team, away_team, season_id):
    """Busca el match_id correspondiente en localhost"""
    
    query = text("""
        SELECT m.id
        FROM matches m
        WHERE m.date = :date
          AND m.season_id = :season_id
        ORDER BY m.id
        LIMIT 1
    """)
    
    with engine_local.connect() as conn:
        result = conn.execute(query, {
            "date": date,
            "season_id": season_id
        }).scalar()
    
    return result


def compare_and_sync(engine_prod, engine_local, dry_run=True):
    """Compara y sincroniza best_bets"""
    
    print_title("🔍 COMPARANDO REGISTROS")
    
    # Obtener datos
    prod_bets = get_best_bets_from_production(engine_prod)
    local_existing = get_existing_bets_from_localhost(engine_local)
    
    # Encontrar faltantes
    missing_bets = []
    
    for bet in prod_bets:
        key = (
            bet['date'].strftime('%Y-%m-%d') if bet['date'] else None,
            bet['home_team'],
            bet['away_team'],
            bet['model'],
            bet['bet_type']
        )
        
        if key not in local_existing:
            missing_bets.append(bet)
    
    print_info(f"Registros faltantes en LOCALHOST: {len(missing_bets)}")
    
    if not missing_bets:
        print_success("¡LOCALHOST está sincronizado con PRODUCCIÓN!")
        return
    
    # Mostrar resumen de faltantes
    print(f"\n{Colors.BOLD}📊 RESUMEN DE REGISTROS FALTANTES:{Colors.END}")
    print(f"{'─'*70}")
    
    for i, bet in enumerate(missing_bets[:10], 1):
        date_str = bet['date'].strftime('%Y-%m-%d') if bet['date'] else 'N/A'
        print(f"{i}. {date_str} | {bet['home_team']} vs {bet['away_team']}")
        print(f"   Modelo: {bet['model']} | Tipo: {bet['bet_type']} | Pred: {bet['prediction']}")
    
    if len(missing_bets) > 10:
        print(f"   ... y {len(missing_bets) - 10} más")
    
    print(f"{'─'*70}\n")
    
    # Confirmar si insertar
    if dry_run:
        print_warning("MODO DRY-RUN: No se insertarán registros")
        print_info("Ejecuta con --insert para insertar los registros")
        return
    
    print_title("💾 INSERTANDO REGISTROS FALTANTES")
    
    inserted = 0
    skipped = 0
    errors = 0
    
    insert_query = text("""
        INSERT INTO best_bets_history (
            match_id, season_id, date, home_team, away_team,
            model, bet_type, prediction,
            confidence, historical_accuracy, combined_score, rank, odds,
            created_at, validated_at, hit, profit_loss, actual_result
        ) VALUES (
            :match_id, :season_id, :date, :home_team, :away_team,
            :model, :bet_type, :prediction,
            :confidence, :historical_accuracy, :combined_score, :rank, :odds,
            :created_at, :validated_at, :hit, :profit_loss, :actual_result
        )
        ON CONFLICT (match_id, model, bet_type) DO NOTHING
    """)
    
    with engine_local.begin() as conn:
        for bet in missing_bets:
            try:
                # Buscar match_id en localhost
                local_match_id = find_match_id_in_localhost(
                    engine_local,
                    bet['date'],
                    bet['home_team'],
                    bet['away_team'],
                    bet['season_id']
                )
                
                if not local_match_id:
                    date_str = bet['date'].strftime('%Y-%m-%d') if bet['date'] else 'N/A'
                    print_warning(f"⚠️  No match: {date_str} {bet['home_team']} vs {bet['away_team']}")
                    skipped += 1
                    continue
                
                # Insertar con match_id local
                conn.execute(insert_query, {
                    "match_id": local_match_id,
                    "season_id": bet['season_id'],
                    "date": bet['date'],
                    "home_team": bet['home_team'],
                    "away_team": bet['away_team'],
                    "model": bet['model'],
                    "bet_type": bet['bet_type'],
                    "prediction": bet['prediction'],
                    "confidence": bet['confidence'],
                    "historical_accuracy": bet['historical_accuracy'],
                    "combined_score": bet['combined_score'],
                    "rank": bet['rank'],
                    "odds": bet['odds'],
                    "created_at": bet['created_at'],
                    "validated_at": bet['validated_at'],
                    "hit": bet['hit'],
                    "profit_loss": bet['profit_loss'],
                    "actual_result": bet['actual_result']
                })
                
                inserted += 1
                
                if inserted % 10 == 0:
                    print_info(f"Insertados: {inserted}/{len(missing_bets)}")
                
            except Exception as e:
                print_error(f"Error insertando bet {bet['prod_id']}: {e}")
                errors += 1
    
    # Resumen final
    print_title("📊 RESUMEN DE SINCRONIZACIÓN")
    print(f"  ✅ Insertados exitosamente: {Colors.GREEN}{inserted}{Colors.END}")
    print(f"  ⚠️  Omitidos (sin match):    {Colors.YELLOW}{skipped}{Colors.END}")
    print(f"  ❌ Errores:                 {Colors.RED}{errors}{Colors.END}")
    print(f"  📦 Total procesados:        {inserted + skipped + errors}")
    print()


def main():
    """Función principal"""
    
    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║         SINCRONIZACIÓN BEST-BETS PROD → LOCALHOST         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")
    
    # Verificar modo
    dry_run = "--insert" not in sys.argv
    
    if dry_run:
        print_warning("🔍 MODO DRY-RUN (solo análisis, no insertará)")
        print_info("Usa: python sync_best_bets.py --insert para insertar\n")
    else:
        print_warning("💾 MODO INSERCIÓN (se insertarán registros)")
        response = input("¿Continuar? (s/n): ")
        if response.lower() != 's':
            print_info("Cancelado por el usuario")
            return
    
    # Conectar
    engine_prod, engine_local = connect_databases()
    
    if not engine_prod or not engine_local:
        print_error("No se pudo conectar a las bases de datos")
        print_info("\nVerifica:")
        print_info("  1. Archivos .env y .env.production existen")
        print_info("  2. Variables DB_HOST, DB_NAME, DB_USER, DB_PASSWORD están definidas")
        print_info("  3. Las bases de datos están accesibles")
        return
    
    # Comparar y sincronizar
    try:
        compare_and_sync(engine_prod, engine_local, dry_run=dry_run)
        print_success("✅ Proceso completado")
    except Exception as e:
        print_error(f"Error durante la sincronización: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()