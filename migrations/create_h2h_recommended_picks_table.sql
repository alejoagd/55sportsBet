-- Tracks the actual outcome of picks shown in the "Top 4" (Pronósticos H2H
-- con Mayor Respaldo Histórico) and "Top 10" (Top 10 Apuestas H2H de Alta
-- Confianza) recommendation lists.
--
-- This is deliberately separate from h2h_scoring: h2h_scoring holds the
-- GENERAL historical accuracy of every (league, stat, score) combination
-- ever seen, used to rank candidates. This table snapshots only the picks
-- that were actually surfaced to users, locked in the first time each
-- (match, stat) pair is recommended (UNIQUE constraint + ON CONFLICT DO
-- NOTHING on insert), so the prediction/line/historical accuracy shown at
-- recommendation time can't drift after the fact - it's a real track record
-- of "did OUR calls come true", not just a re-read of the general average.

CREATE TABLE IF NOT EXISTS h2h_recommended_picks (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL,

    stat VARCHAR(30) NOT NULL,
    score INTEGER NOT NULL,
    league VARCHAR(100) NOT NULL,
    prediction VARCHAR(30) NOT NULL,
    line NUMERIC,

    -- Contexto histórico en el momento en que se recomendó (para auditar
    -- si el criterio de selección cambió con el tiempo)
    historical_accuracy_at_time NUMERIC(5, 2),
    historical_sample_at_time INTEGER,

    -- Resultado real, una vez jugado el partido
    hit BOOLEAN,
    actual_total NUMERIC,

    recommended_at TIMESTAMP DEFAULT NOW(),
    validated_at TIMESTAMP,

    CONSTRAINT fk_h2h_recommended_pick_match FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,
    CONSTRAINT unique_h2h_recommended_pick UNIQUE (match_id, stat)
);

CREATE INDEX IF NOT EXISTS idx_h2h_recommended_picks_match_id ON h2h_recommended_picks(match_id);
CREATE INDEX IF NOT EXISTS idx_h2h_recommended_picks_score ON h2h_recommended_picks(score);
CREATE INDEX IF NOT EXISTS idx_h2h_recommended_picks_hit ON h2h_recommended_picks(hit);

COMMENT ON TABLE h2h_recommended_picks IS 'Track record of picks actually shown in the Top 4 / Top 10 H2H recommendation lists - snapshotted once per (match, stat), validated against the real match result once played.';
