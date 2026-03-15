-- Create table to store H2H scoring results
-- This table stores the score (0-12) for each betting line prediction
-- The score represents how many of the last 12 H2H matches would have hit this prediction

CREATE TABLE IF NOT EXISTS h2h_scoring (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL,

    -- Goles
    goles_score INTEGER,
    goles_prediction VARCHAR(20),
    goles_hit BOOLEAN,

    -- Tiros
    tiros_score INTEGER,
    tiros_prediction VARCHAR(20),
    tiros_hit BOOLEAN,

    -- Tiros al arco
    tiros_al_arco_score INTEGER,
    tiros_al_arco_prediction VARCHAR(20),
    tiros_al_arco_hit BOOLEAN,

    -- Corners
    corners_score INTEGER,
    corners_prediction VARCHAR(20),
    corners_hit BOOLEAN,

    -- Tarjetas
    tarjetas_score INTEGER,
    tarjetas_prediction VARCHAR(20),
    tarjetas_hit BOOLEAN,

    -- Faltas
    faltas_score INTEGER,
    faltas_prediction VARCHAR(20),
    faltas_hit BOOLEAN,

    -- Overall confidence (average of all scores)
    overall_confidence NUMERIC(5, 2),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- Foreign key - references matches.id (not match_id)
    CONSTRAINT fk_match FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE,

    -- Unique constraint: one H2H scoring per match
    CONSTRAINT unique_h2h_per_match UNIQUE (match_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_h2h_scoring_match_id ON h2h_scoring(match_id);
CREATE INDEX IF NOT EXISTS idx_h2h_scoring_goles_score ON h2h_scoring(goles_score);
CREATE INDEX IF NOT EXISTS idx_h2h_scoring_tiros_score ON h2h_scoring(tiros_score);
CREATE INDEX IF NOT EXISTS idx_h2h_scoring_corners_score ON h2h_scoring(corners_score);

-- Add comment
COMMENT ON TABLE h2h_scoring IS 'Stores H2H scoring results (0-12) for each betting line, based on last 12 direct confrontations';
