# verificar_partidos_futuros.py
from sqlalchemy import create_engine, text
from src.config import settings

engine = create_engine(settings.sqlalchemy_url)

with engine.begin() as conn:
    query = text("""
        SELECT 
            l.name as liga,
            COUNT(*) as partidos_futuros,
            MIN(m.date) as proximo_partido,
            MAX(m.date) as ultimo_partido
        FROM matches m
        JOIN seasons s ON s.id = m.season_id
        JOIN leagues l ON l.id = s.league_id
        WHERE m.date >= CURRENT_DATE
          AND m.home_goals IS NULL
        GROUP BY l.id, l.name
        ORDER BY l.name
    """)
    
    print("\n" + "="*70)
    print("  PARTIDOS FUTUROS POR LIGA")
    print("="*70 + "\n")
    
    for row in conn.execute(query):
        print(f"{row.liga:20} | Futuros: {row.partidos_futuros:4} | Próximo: {row.proximo_partido}")
    
    print("\n" + "="*70 + "\n")
