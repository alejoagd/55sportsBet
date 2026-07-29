-- Adds real kickoff timestamp to matches (previously only a bare DATE was
-- stored, which forced the frontend to fabricate an identical fake time for
-- every match and caused evening South American kickoffs to land on the
-- wrong UTC calendar day) and a team crest URL sourced from ESPN.

ALTER TABLE matches ADD COLUMN IF NOT EXISTS kickoff_at TIMESTAMPTZ;
CREATE INDEX IF NOT EXISTS idx_matches_kickoff_at ON matches(kickoff_at);

ALTER TABLE teams ADD COLUMN IF NOT EXISTS logo_url VARCHAR(255);
