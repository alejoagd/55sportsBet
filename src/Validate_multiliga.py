#!/usr/bin/env python3
"""
Script de validación final para sistema multi-liga.

Valida que tu estructura de base de datos está correctamente configurada
para soportar múltiples ligas de forma independiente.

Uso:
    python validate_multiliga_FINAL.py
"""

from sqlalchemy import create_engine, text
from config import settings
from tabulate import tabulate
import sys


def print_header(title: str):
    """Imprime un encabezado formateado"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def check_1_tables_exist(conn) -> bool:
    """Verifica que todas las tablas necesarias existen"""
    print_header("CHECK 1: TABLAS NECESARIAS")
    
    required_tables = [
        ('leagues', True),
        ('seasons', True),
        ('matches', True),
        ('teams', True),
        ('poisson_predictions', True),
        ('weinston_predictions', True),
        ('weinston_params', True),
        ('weinston_ratings', True),
        ('prediction_outcomes', True),
        ('league_parameters', False),  # Opcional pero recomendada
        ('match_stats', False),
    ]
    
    all_ok = True
    results = []
    
    for table_name, is_required in required_tables:
        query = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = :table_name
            )
        """)
        exists = conn.execute(query, {"table_name": table_name}).scalar()
        
        if is_required:
            status = "✅ OK" if exists else "❌ FALTA"
            if not exists:
                all_ok = False
        else:
            status = "✅ OK" if exists else "⚠️  Opcional"
        
        results.append([table_name, "Requerida" if is_required else "Opcional", status])
    
    print(tabulate(results, headers=["Tabla", "Tipo", "Estado"], tablefmt="simple"))
    
    return all_ok


def check_2_league_id_in_seasons(conn) -> bool:
    """Verifica que seasons tiene league_id y está asignado"""
    print_header("CHECK 2: COLUMNA league_id EN seasons")
    
    # Verificar que columna existe
    query = text("""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name = 'seasons' AND column_name = 'league_id'
    """)
    
    if not conn.execute(query).scalar():
        print("❌ ERROR: Columna 'league_id' no existe en tabla 'seasons'")
        return False
    
    print("✅ Columna 'league_id' existe")
    
    # Verificar asignación
    query = text("""
        SELECT 
            COUNT(*) as total,
            COUNT(league_id) as con_league_id,
            COUNT(*) - COUNT(league_id) as sin_league_id
        FROM seasons
    """)
    
    row = conn.execute(query).one()
    
    results = [
        ["Total temporadas", row.total],
        ["Con league_id asignado", row.con_league_id],
        ["Sin league_id", row.sin_league_id],
    ]
    
    print(tabulate(results, headers=["Métrica", "Valor"], tablefmt="simple"))
    
    if row.sin_league_id > 0:
        print(f"\n⚠️  ADVERTENCIA: {row.sin_league_id} temporadas sin league_id")
        
        # Mostrar cuáles
        query = text("""
            SELECT id, year_start, year_end 
            FROM seasons 
            WHERE league_id IS NULL
            LIMIT 5
        """)
        missing = conn.execute(query).fetchall()
        
        print("\n   Temporadas sin asignar (primeras 5):")
        for s in missing:
            print(f"   - Season {s.id}: {s.year_start}/{s.year_end}")
        
        return False
    
    print("\n✅ Todas las temporadas tienen league_id asignado")
    return True


def check_3_league_id_in_weinston_tables(conn) -> bool:
    """Verifica que weinston_params y weinston_ratings tienen league_id"""
    print_header("CHECK 3: COLUMNA league_id EN TABLAS WEINSTON")
    
    tables_to_check = ['weinston_params', 'weinston_ratings']
    all_ok = True
    
    for table_name in tables_to_check:
        # Verificar columna existe
        query = text(f"""
            SELECT column_name 
            FROM information_schema.columns
            WHERE table_name = :table_name AND column_name = 'league_id'
        """)
        
        if not conn.execute(query, {"table_name": table_name}).scalar():
            print(f"❌ ERROR: Columna 'league_id' no existe en '{table_name}'")
            all_ok = False
            continue
        
        # Verificar asignación
        query = text(f"""
            SELECT 
                COUNT(*) as total,
                COUNT(league_id) as con_league_id,
                COUNT(*) - COUNT(league_id) as sin_league_id
            FROM {table_name}
        """)
        
        row = conn.execute(query).one()
        
        status = "✅ OK" if row.sin_league_id == 0 else f"⚠️  {row.sin_league_id} sin asignar"
        print(f"{table_name:25} | Total: {row.total:5} | Con league_id: {row.con_league_id:5} | {status}")
        
        if row.sin_league_id > 0:
            all_ok = False
    
    return all_ok


def check_4_leagues_configured(conn) -> bool:
    """Verifica que hay ligas configuradas con datos"""
    print_header("CHECK 4: LIGAS CONFIGURADAS")
    
    query = text("""
        SELECT 
            l.id,
            l.name,
            l.country,
            COUNT(DISTINCT s.id) as temporadas,
            COUNT(DISTINCT m.id) as partidos,
            MIN(s.year_start) as primera,
            MAX(s.year_start) as ultima
        FROM leagues l
        LEFT JOIN seasons s ON s.league_id = l.id
        LEFT JOIN matches m ON m.season_id = s.id
        GROUP BY l.id, l.name, l.country
        HAVING COUNT(DISTINCT s.id) > 0  -- Solo ligas con temporadas
        ORDER BY COUNT(DISTINCT m.id) DESC
    """)
    
    leagues = conn.execute(query).mappings().all()
    
    if not leagues:
        print("❌ ERROR: No hay ligas configuradas")
        return False
    
    results = []
    for league in leagues:
        status = "✅ Activa" if league['partidos'] > 0 else "⚠️  Sin datos"
        results.append([
            league['name'],
            league['country'],
            league['temporadas'],
            f"{league['partidos']:,}",
            f"{league['primera']}-{league['ultima']}",
            status
        ])
    
    print(tabulate(
        results, 
        headers=["Liga", "País", "Temporadas", "Partidos", "Años", "Estado"],
        tablefmt="simple"
    ))
    
    active_leagues = sum(1 for l in leagues if l['partidos'] > 0)
    print(f"\n✅ {active_leagues} liga(s) activa(s) con datos")
    
    return active_leagues >= 2  # Al menos Premier + La Liga


def check_5_league_parameters(conn) -> bool:
    """Verifica que league_parameters tiene datos calculados"""
    print_header("CHECK 5: PARÁMETROS DE LIGA")
    
    query = text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'league_parameters'
        )
    """)
    
    if not conn.execute(query).scalar():
        print("⚠️  Tabla 'league_parameters' no existe (opcional)")
        print("   Los parámetros se calcularán dinámicamente")
        return True  # Es opcional, no falla el check
    
    query = text("""
        SELECT 
            l.name as liga,
            lp.avg_home_goals,
            lp.avg_away_goals,
            lp.home_field_advantage,
            lp.sample_size
        FROM league_parameters lp
        JOIN leagues l ON l.id = lp.league_id
        ORDER BY l.name
    """)
    
    params = conn.execute(query).mappings().all()
    
    if not params:
        print("⚠️  Tabla existe pero está vacía")
        print("   Ejecutar: SELECT calculate_league_parameters(<league_id>);")
        return True  # No crítico
    
    results = []
    for p in params:
        if p['sample_size'] == 0:
            status = "⚠️  Sin datos"
        elif p['sample_size'] < 100:
            status = f"⚠️  Pocos datos ({p['sample_size']})"
        else:
            status = "✅ OK"
        
        results.append([
            p['liga'],
            f"{p['avg_home_goals']:.3f}" if p['avg_home_goals'] else "NULL",
            f"{p['avg_away_goals']:.3f}" if p['avg_away_goals'] else "NULL",
            f"{p['home_field_advantage']:.3f}" if p['home_field_advantage'] else "NULL",
            f"{p['sample_size']:,}" if p['sample_size'] else "0",
            status
        ])
    
    print(tabulate(
        results,
        headers=["Liga", "Avg Home", "Avg Away", "HFA", "Sample Size", "Estado"],
        tablefmt="simple"
    ))
    
    return True


def check_6_independence(conn) -> bool:
    """Verifica que las ligas tienen métricas independientes"""
    print_header("CHECK 6: INDEPENDENCIA ENTRE LIGAS")
    
    query = text("""
        SELECT 
            l.name as liga,
            AVG(m.home_goals)::float as avg_home,
            AVG(m.away_goals)::float as avg_away,
            COUNT(*) as partidos
        FROM matches m
        JOIN seasons s ON s.id = m.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE m.home_goals IS NOT NULL
          AND m.away_goals IS NOT NULL
        GROUP BY l.id, l.name
        HAVING COUNT(*) > 100  -- Solo ligas con suficientes datos
        ORDER BY l.name
    """)
    
    leagues = conn.execute(query).mappings().all()
    
    if len(leagues) < 2:
        print("⚠️  Solo hay 1 liga con datos, no se puede verificar independencia")
        return True  # No es error, simplemente no hay con qué comparar
    
    results = []
    for league in leagues:
        results.append([
            league['liga'],
            f"{league['avg_home']:.3f}",
            f"{league['avg_away']:.3f}",
            f"{(league['avg_home'] + league['avg_away'])/2:.3f}",
            f"{league['partidos']:,}"
        ])
    
    print(tabulate(
        results,
        headers=["Liga", "Avg Home", "Avg Away", "Avg Total", "Partidos"],
        tablefmt="simple"
    ))
    
    # Verificar que NO todas las ligas tienen el mismo promedio
    avgs = [l['avg_home'] for l in leagues]
    all_same = all(abs(avg - avgs[0]) < 0.01 for avg in avgs)
    
    if all_same:
        print("\n❌ ERROR: Todas las ligas tienen promedios idénticos")
        print("   Esto indica que los datos no están separados correctamente")
        return False
    
    print("\n✅ Las ligas tienen métricas diferentes (como se espera)")
    return True


def check_7_predictions_coverage(conn) -> bool:
    """Verifica cobertura de predicciones por liga"""
    print_header("CHECK 7: COBERTURA DE PREDICCIONES")
    
    query = text("""
        SELECT 
            l.name as liga,
            COUNT(DISTINCT m.id) as total_partidos,
            COUNT(DISTINCT pp.match_id) as con_poisson,
            COUNT(DISTINCT wp.match_id) as con_weinston,
            ROUND(COUNT(DISTINCT pp.match_id)::numeric / NULLIF(COUNT(DISTINCT m.id), 0) * 100, 1) as cobertura_poisson,
            ROUND(COUNT(DISTINCT wp.match_id)::numeric / NULLIF(COUNT(DISTINCT m.id), 0) * 100, 1) as cobertura_weinston
        FROM leagues l
        JOIN seasons s ON s.league_id = l.id
        JOIN matches m ON m.season_id = s.id
        LEFT JOIN poisson_predictions pp ON pp.match_id = m.id
        LEFT JOIN weinston_predictions wp ON wp.match_id = m.id
        WHERE m.home_goals IS NOT NULL  -- Solo partidos jugados
        GROUP BY l.id, l.name
        HAVING COUNT(DISTINCT m.id) > 0
        ORDER BY l.name
    """)
    
    leagues = conn.execute(query).mappings().all()
    
    results = []
    for league in leagues:
        status_p = "✅" if league['cobertura_poisson'] > 80 else ("⚠️ " if league['cobertura_poisson'] > 50 else "❌")
        status_w = "✅" if league['cobertura_weinston'] > 80 else ("⚠️ " if league['cobertura_weinston'] > 50 else "❌")
        
        results.append([
            league['liga'],
            f"{league['total_partidos']:,}",
            f"{league['con_poisson']:,}",
            f"{league['cobertura_poisson']}% {status_p}",
            f"{league['con_weinston']:,}",
            f"{league['cobertura_weinston']}% {status_w}"
        ])
    
    print(tabulate(
        results,
        headers=["Liga", "Total", "Poisson", "Cob %", "Weinston", "Cob %"],
        tablefmt="simple"
    ))
    
    print("\n📊 Cobertura mínima recomendada: 80%")
    
    return True  # No crítico, solo informativo


def main():
    """Función principal"""
    print("\n" + "🔍 VALIDACIÓN SISTEMA MULTI-LIGA ".center(80, "="))
    print("Base de datos real con leagues/seasons existentes")
    print("="*80 + "\n")
    
    engine = create_engine(settings.sqlalchemy_url)
    
    checks = []
    
    with engine.begin() as conn:
        checks.append(("Tablas necesarias", check_1_tables_exist(conn)))
        checks.append(("league_id en seasons", check_2_league_id_in_seasons(conn)))
        checks.append(("league_id en weinston", check_3_league_id_in_weinston_tables(conn)))
        checks.append(("Ligas configuradas", check_4_leagues_configured(conn)))
        checks.append(("Parámetros de liga", check_5_league_parameters(conn)))
        checks.append(("Independencia", check_6_independence(conn)))
        checks.append(("Cobertura predicciones", check_7_predictions_coverage(conn)))
    
    # Resumen
    print_header("RESUMEN")
    
    results = []
    all_passed = True
    
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        results.append([check_name, status])
        if not passed:
            all_passed = False
    
    print(tabulate(results, headers=["Check", "Estado"], tablefmt="simple"))
    
    print("\n" + "="*80)
    
    if all_passed:
        print("🎉 " + "¡VALIDACIÓN EXITOSA!".center(76) + " 🎉")
        print("\nTu sistema está correctamente configurado para múltiples ligas.")
        print("\n📋 Próximos pasos:")
        print("   1. Copiar league_context_FINAL.py a src/predictions/league_context.py")
        print("   2. Refactorizar upcoming_core.py usando el patrón mostrado")
        print("   3. Probar con: python -m src.predictions.cli upcoming --season-id <ID>")
    else:
        print("⚠️  " + "HAY PROBLEMAS QUE RESOLVER".center(72) + " ⚠️ ")
        print("\nRevisa los errores arriba y ejecuta las correcciones necesarias.")
    
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())