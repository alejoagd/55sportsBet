# test_league_context.py
from sqlalchemy import create_engine, text
from src.config import settings
from src.predictions.league_context import LeagueContext

engine = create_engine(settings.sqlalchemy_url)

print("\n" + "="*70)
print("  PRUEBA DE LEAGUE CONTEXT")
print("="*70)

with engine.begin() as conn:
    # 1. Buscar temporada más reciente de Premier League
    query = text("""
        SELECT s.id, s.year_start, s.year_end, l.name 
        FROM seasons s
        JOIN leagues l ON l.id = s.league_id
        WHERE l.name = 'Premier League'
        ORDER BY s.year_start DESC
        LIMIT 1
    """)
    
    row = conn.execute(query).one()
    premier_season_id = row.id
    print(f"\n🏴󠁧󠁢󠁥󠁮󠁧󠁿 PREMIER LEAGUE (Season {row.id}: {row.year_start}/{row.year_end})")
    print("-" * 70)
    
    ctx_pl = LeagueContext.from_season(conn, premier_season_id)
    print(f"\n📊 Resultado: {ctx_pl}\n")
    
    # 2. Buscar temporada más reciente de La Liga
    query = text("""
        SELECT s.id, s.year_start, s.year_end, l.name 
        FROM seasons s
        JOIN leagues l ON l.id = s.league_id
        WHERE l.name = 'La Liga'
        ORDER BY s.year_start DESC
        LIMIT 1
    """)
    
    row = conn.execute(query).one()
    laliga_season_id = row.id
    print(f"\n🇪🇸 LA LIGA (Season {row.id}: {row.year_start}/{row.year_end})")
    print("-" * 70)
    
    ctx_ll = LeagueContext.from_season(conn, laliga_season_id)
    print(f"\n📊 Resultado: {ctx_ll}\n")
    
    # 3. Verificar independencia
    print("\n" + "="*70)
    print("  VERIFICACIÓN DE INDEPENDENCIA")
    print("="*70)
    print(f"\nPremier League avg_home_goals: {ctx_pl.avg_home_goals:.3f}")
    print(f"La Liga avg_home_goals:        {ctx_ll.avg_home_goals:.3f}")
    print(f"Diferencia:                    {abs(ctx_pl.avg_home_goals - ctx_ll.avg_home_goals):.3f}")
    
    if abs(ctx_pl.avg_home_goals - ctx_ll.avg_home_goals) > 0.01:
        print("\n✅ ¡ÉXITO! Las ligas tienen promedios DIFERENTES")
        print("   El sistema está correctamente separado por liga.")
    else:
        print("\n❌ ERROR: Las ligas tienen promedios IDÉNTICOS")
        print("   Hay un problema con la separación de datos.")
    
    print("\n" + "="*70)
    print(f"\n📝 Season IDs para usar en próximos tests:")
    print(f"   Premier League: {premier_season_id}")
    print(f"   La Liga:        {laliga_season_id}")
    print("\n")