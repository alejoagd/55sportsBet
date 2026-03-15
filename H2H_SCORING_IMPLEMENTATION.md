# H2H Scoring System - Implementation Guide

## Overview

The H2H Scoring System analyzes the last 12 direct confrontations between two teams and calculates how many times a current prediction would have been correct historically. This gives a score from 0-12 that indicates historical reliability.

## Solution Architecture

### 1. Database Table: `h2h_scoring`

Created a new table to store H2H scoring results for each match.

**Location:** `migrations/create_h2h_scoring_table.sql`

**Schema:**
```sql
CREATE TABLE h2h_scoring (
    id SERIAL PRIMARY KEY,
    match_id INTEGER NOT NULL UNIQUE,

    -- Scores (0-12) for each stat type
    goles_score INTEGER,
    tiros_score INTEGER,
    tiros_al_arco_score INTEGER,
    corners_score INTEGER,
    tarjetas_score INTEGER,
    faltas_score INTEGER,

    -- Predictions
    goles_prediction VARCHAR(20),
    tiros_prediction VARCHAR(20),
    ... etc

    -- Hit/miss results (populated after match finishes)
    goles_hit BOOLEAN,
    tiros_hit BOOLEAN,
    ... etc

    -- Overall confidence
    overall_confidence NUMERIC(5, 2),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### 2. Backend: Save H2H Scores

**Location:** `src/predictions/h2h_scoring_system.py`

**New Function:** `save_h2h_scoring_to_db(match_id, scoring_results, overall_confidence)`

This function:
- Takes the H2H scoring results
- Saves scores (0-12) to the database
- Uses INSERT ... ON CONFLICT to handle updates

**Modified Function:** `calculate_h2h_scoring()`

Now automatically saves results to database after calculation.

### 3. API Endpoint

**Location:** `src/api.py`

**Endpoint:** `GET /api/h2h-score/effectiveness-by-league`

**Updated Query:**
- Reads from `h2h_scoring` table (not betting_lines_predictions)
- Groups by league, stat type, and score (0-12)
- Returns hits, misses, total, and accuracy for each score
- Includes all 6 stat types: GOLES, TIROS, TIROS AL ARCO, CORNERS, TARJETAS, FALTAS

### 4. Frontend Display

**Location:** `frontend/src/BettingLinesStats.tsx`

**Features:**
- Displays H2H effectiveness section after betting lines stats
- Shows granular detail (individual scores 0-12)
- Responsive grid layout (1/2/3 columns based on screen size)
- Color-coded accuracy indicators
- Separate table for each stat type within each league

## How to Deploy

### Step 1: Create Database Table

Run the migration script:

```bash
psql -U your_user -d your_database -f migrations/create_h2h_scoring_table.sql
```

### Step 2: Populate H2H Scores (IMPORTANT!)

You need to calculate and save H2H scores for existing matches. Options:

**Option A: Run for all past matches**
Create a script that loops through all matches and calls `calculate_h2h_scoring()`:

```python
from src.predictions.h2h_scoring_system import calculate_h2h_scoring
from src.db import engine
from sqlalchemy import text

with engine.begin() as conn:
    # Get all matches that have weinston predictions
    matches = conn.execute(text("""
        SELECT DISTINCT m.match_id, m.home_team_id, m.away_team_id, m.season_id
        FROM matches m
        JOIN weinston_predictions wp ON wp.match_id = m.id
        WHERE m.match_id IS NOT NULL
        ORDER BY m.date
    """)).fetchall()

    for match in matches:
        try:
            result = calculate_h2h_scoring(
                match.match_id,
                match.home_team_id,
                match.away_team_id,
                match.season_id
            )
            print(f"✅ Processed match {match.match_id}")
        except Exception as e:
            print(f"❌ Error processing match {match.match_id}: {e}")
```

**Option B: Run as part of workflow**
Integrate `calculate_h2h_scoring()` into your existing prediction workflow so it runs automatically for new matches.

### Step 3: Update Hit/Miss Results

After matches are played, you need to update the `*_hit` columns with actual results. This should be part of your evaluation workflow.

```python
# Example: Update hits after match is played
with engine.begin() as conn:
    conn.execute(text("""
        UPDATE h2h_scoring h2h
        SET
            tiros_hit = (
                SELECT blp.shots_hit
                FROM betting_lines_predictions blp
                WHERE blp.match_id = h2h.match_id
                LIMIT 1
            ),
            corners_hit = (
                SELECT blp.corners_hit
                FROM betting_lines_predictions blp
                WHERE blp.match_id = h2h.match_id
                LIMIT 1
            ),
            -- ... etc for all stats
            updated_at = NOW()
        WHERE h2h.match_id = :match_id
    """), {"match_id": match_id})
```

### Step 4: Deploy Code Changes

```bash
git add migrations/create_h2h_scoring_table.sql
git add src/predictions/h2h_scoring_system.py
git add src/api.py
git add frontend/src/BettingLinesStats.tsx
git commit -m "Implement H2H scoring system with database storage and effectiveness display"
git push origin main
```

## Data Flow

```
1. Before Match:
   calculate_h2h_scoring()
   → Analyzes last 12 H2H matches
   → Calculates scores (0-12) for each stat
   → save_h2h_scoring_to_db()
   → Stores in h2h_scoring table

2. After Match:
   Evaluation process
   → Checks if predictions were correct
   → Updates *_hit columns in h2h_scoring table

3. Display:
   Frontend calls /api/h2h-score/effectiveness-by-league
   → API reads from h2h_scoring table
   → Groups by league, stat, score
   → Returns accuracy data
   → Frontend displays in tables
```

## Key Differences from Before

**Before (INCORRECT):**
- Tried to convert confidence (0.0-1.0) to score (0-12)
- Confidence and H2H score are DIFFERENT things
- No database storage of H2H scores

**After (CORRECT):**
- H2H scores calculated from actual H2H match analysis
- Scores stored in dedicated table
- Separate from confidence calculation
- Can track effectiveness over time

## Next Steps

1. ✅ Create database table
2. ⏳ Populate H2H scores for existing matches
3. ⏳ Test API endpoint with real data
4. ⏳ Verify frontend display
5. ⏳ Integrate into automated workflow

## Notes

- H2H Score (0-12): How many of last 12 H2H matches the prediction would have hit
- Confidence (0.0-1.0): How close prediction is to betting line
- These are INDEPENDENT metrics that serve different purposes
