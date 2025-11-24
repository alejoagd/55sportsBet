# test_upcoming_core.py
from sqlalchemy import create_engine
from src.config import settings
from src.predictions.league_context import LeagueContext
from src.predictions.upcoming_core import load_team_strengths, load_team_stat_profiles

engine = create_engine(settings.sqlalchemy_url)

print("\n" + "="*70)
print("  PRUEBA DE UPCOMING_CORE REFACTORIZADO")
print("="*70)

with engine.begin() as conn:
    # Test con Premier League (season_id = 2)
    print("\n🏴󠁧󠁢󠁥󠁮󠁧󠁿 TEST 1: PREMIER LEAGUE (Season 2)")
    print("-"*70)
    
    ctx_pl = LeagueContext.from_season(conn, 2)
    
    strengths_pl, lg_home, lg_away, hfa = load_team_strengths(
        conn, 2, league_ctx=ctx_pl
    )
    
    print(f"\n📊 Resultados:")
    print(f"   Equipos con fortalezas: {len(strengths_pl)}")
    print(f"   Promedios retornados: {lg_home:.3f} / {lg_away:.3f}")
    print(f"   HFA: {hfa:.3f}")
    
    if len(strengths_pl) > 0:
        # Mostrar un equipo de ejemplo
        sample_team_id = list(strengths_pl.keys())[0]
        sample = strengths_pl[sample_team_id]
        print(f"\n   Ejemplo - Team {sample_team_id}:")
        print(f"      Attack Home:  {sample['attack_home']:.3f}")
        print(f"      Defense Home: {sample['defense_home']:.3f}")
        print(f"      Attack Away:  {sample['attack_away']:.3f}")
        print(f"      Defense Away: {sample['defense_away']:.3f}")
    
    # Test con La Liga (season_id = 15)
    print("\n\n🇪🇸 TEST 2: LA LIGA (Season 15)")
    print("-"*70)
    
    ctx_ll = LeagueContext.from_season(conn, 15)
    
    strengths_ll, lg_home, lg_away, hfa = load_team_strengths(
        conn, 15, league_ctx=ctx_ll
    )
    
    print(f"\n📊 Resultados:")
    print(f"   Equipos con fortalezas: {len(strengths_ll)}")
    print(f"   Promedios retornados: {lg_home:.3f} / {lg_away:.3f}")
    print(f"   HFA: {hfa:.3f}")
    
    if len(strengths_ll) > 0:
        # Mostrar un equipo de ejemplo
        sample_team_id = list(strengths_ll.keys())[0]
        sample = strengths_ll[sample_team_id]
        print(f"\n   Ejemplo - Team {sample_team_id}:")
        print(f"      Attack Home:  {sample['attack_home']:.3f}")
        print(f"      Defense Home: {sample['defense_home']:.3f}")
        print(f"      Attack Away:  {sample['attack_away']:.3f}")
        print(f"      Defense Away: {sample['defense_away']:.3f}")
    
    # Verificar independencia
    print("\n\n" + "="*70)
    print("  VERIFICACIÓN DE INDEPENDENCIA")
    print("="*70)
    
    if len(strengths_pl) > 0 and len(strengths_ll) > 0:
        print(f"\n✅ Premier League: {len(strengths_pl)} equipos procesados")
        print(f"✅ La Liga: {len(strengths_ll)} equipos procesados")
        
        # Verificar que los equipos son diferentes
        teams_pl = set(strengths_pl.keys())
        teams_ll = set(strengths_ll.keys())
        overlap = teams_pl & teams_ll
        
        print(f"\n📊 Equipos en común entre ligas: {len(overlap)}")
        if len(overlap) == 0:
            print("   ✅ PERFECTO! Las ligas están completamente separadas")
        else:
            print(f"   ⚠️  Hay {len(overlap)} equipos en ambas ligas")
            print(f"   (Esto puede ser normal si hay equipos con mismo ID)")
    else:
        print("\n❌ ERROR: Alguna liga no tiene equipos procesados")
        if len(strengths_pl) == 0:
            print("   Premier League: 0 equipos")
        if len(strengths_ll) == 0:
            print("   La Liga: 0 equipos")

print("\n" + "="*70)
print("  ✅ PRUEBA COMPLETADA")
print("="*70 + "\n")