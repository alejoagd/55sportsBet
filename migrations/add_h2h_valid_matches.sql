-- Denominador del H2H Score: cuántos de los últimos 12 enfrentamientos tenían
-- dato de esa estadística (el "4" de un 2/4). Sin él no se puede saber si un
-- puntaje de 2 salió de 2 partidos o de 12, y se mezclaban en las estadísticas.
-- Columnas nuevas, sin default: las filas existentes quedan en NULL hasta
-- recontarlas con  python -m src.scripts.recount_h2h_scoring --apply
-- (api.py lo aplica también al arrancar con ALTER TABLE ... IF NOT EXISTS).
ALTER TABLE h2h_scoring
    ADD COLUMN IF NOT EXISTS goles_valid         INTEGER,
    ADD COLUMN IF NOT EXISTS tiros_valid         INTEGER,
    ADD COLUMN IF NOT EXISTS tiros_al_arco_valid INTEGER,
    ADD COLUMN IF NOT EXISTS corners_valid       INTEGER,
    ADD COLUMN IF NOT EXISTS tarjetas_valid      INTEGER,
    ADD COLUMN IF NOT EXISTS faltas_valid        INTEGER;

ALTER TABLE h2h_recommended_picks
    ADD COLUMN IF NOT EXISTS valid_matches INTEGER;
