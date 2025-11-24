# test_upcoming_weinston.py
from sqlalchemy import create_engine, text
from src.config import settings
from src.predictions.league_context import LeagueContext
from src.predictions.upcoming_weinston import predict_and_upsert_weinston

engine = create_engine(settings.sqlalchemy_url)

print("\n" + "="*70)
print("  PRUEBA DE UPCOMING_WEINSTON REFACTORIZADO")
print("="*70)

with engine.begin() as conn:
    # Obtener algunos partidos futuros de Premier League
    query = text("""
        SELECT m.id 
        FROM matches m
        JOIN seasons s ON s.id = m.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE l.name = 'Premier League'
          AND m.date >= CURRENT_DATE
          AND m.home_goals IS NULL
        ORDER BY m.date
        LIMIT 5
    """)
    
    match_ids_pl = [row[0] for row in conn.execute(query)]
    
    if match_ids_pl:
        print(f"\n🏴󠁧󠁢󠁥󠁮󠁧󠁿 TEST: PREMIER LEAGUE")
        print("-"*70)
        print(f"Partidos futuros encontrados: {len(match_ids_pl)}")
        
        # Cargar contexto
        ctx_pl = LeagueContext.from_season(conn, 2)
        
        # Generar predicciones
        predict_and_upsert_weinston(conn, 2, match_ids_pl, league_ctx=ctx_pl)
        
        # Verificar que se guardaron
        verify = text("""
            SELECT COUNT(*) 
            FROM weinston_predictions 
            WHERE match_id = ANY(:ids)
        """)
        count = conn.execute(verify, {"ids": match_ids_pl}).scalar()
        print(f"\n✅ Verificación: {count}/{len(match_ids_pl)} predicciones en BD")
    else:
        print("\n⚠️  No hay partidos futuros de Premier League")

print("\n" + "="*70)
print("  ✅ PRUEBA COMPLETADA")
print("="*70 + "\n")