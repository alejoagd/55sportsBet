-- Estado en vivo de los partidos (sondeo de ESPN, src/live/poller.py).
-- Los marcadores parciales viven aquí y NO en matches: evaluate() y las posiciones tratan
-- cualquier partido con goles en matches como terminado. Solo al finalizar el partido el
-- resultado pasa a matches.home_goals/away_goals. Se aplica a mano (y poller.py crea la
-- tabla si no existe).
CREATE TABLE IF NOT EXISTS match_live (
    match_id      INTEGER PRIMARY KEY REFERENCES matches(id) ON DELETE CASCADE,
    espn_event_id BIGINT NOT NULL,
    state         TEXT NOT NULL,            -- pre | in | post
    status_name   TEXT,                     -- STATUS_FIRST_HALF, STATUS_SHOOTOUT, STATUS_FULL_TIME...
    detail        TEXT,                     -- "HT", "73'", "Penalties", "FT-Pens"
    clock         TEXT,
    period        INTEGER,
    home_score    INTEGER,
    away_score    INTEGER,
    home_shootout INTEGER,
    away_shootout INTEGER,
    plays         JSONB NOT NULL DEFAULT '[]'::jsonb,
    first_live_at TIMESTAMPTZ,
    finished_at   TIMESTAMPTZ,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_match_live_state ON match_live (state);
