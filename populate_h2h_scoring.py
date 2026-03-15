"""
Script to populate h2h_scoring table with historical data.

This script:
1. Finds all matches with Weinston predictions
2. Calculates H2H scores (0-12) for each match
3. Determines hit/miss results based on actual betting lines outcomes
4. Inserts data into h2h_scoring table
"""

from sqlalchemy import text
from src.db import engine
from src.predictions.h2h_scoring_system import calculate_h2h_scoring
import sys


def get_matches_to_process(limit=None):
    """
    Get all matches that have:
    - Weinston predictions
    - Betting lines predictions (to check hits/misses)
    - Actual match results (match has finished)
    """
    with engine.begin() as conn:
        query = text("""
            SELECT DISTINCT
                m.id as match_id,
                m.home_team_id,
                m.away_team_id,
                m.season_id,
                m.date,
                l.name as league_name
            FROM matches m
            JOIN seasons s ON s.id = m.season_id
            JOIN leagues l ON l.id = s.league_id
            JOIN weinston_predictions wp ON wp.match_id = m.id
            JOIN betting_lines_predictions blp ON blp.match_id = m.id
            WHERE m.date < CURRENT_DATE  -- Only past matches
            AND blp.actual_total_shots IS NOT NULL  -- Match results are available
            ORDER BY m.date DESC
            LIMIT :limit
        """)

        params = {"limit": limit if limit else 10000}
        results = conn.execute(query, params).fetchall()

        return [dict(row._mapping) for row in results]


def calculate_and_save_h2h_score(match):
    """
    Calculate H2H score for a match and save to database.
    Returns True if successful, False otherwise.
    """
    try:
        # Calculate H2H scoring
        result = calculate_h2h_scoring(
            match_id=match['match_id'],
            home_team_id=match['home_team_id'],
            away_team_id=match['away_team_id'],
            season_id=match['season_id']
        )

        if 'error' in result:
            print(f"  ⚠️  Skipped: {result['error']}")
            return False

        print(f"  ✅ Calculated H2H scores (confidence: {result['overall_confidence']})")
        return True

    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def update_hit_results(match_id):
    """
    Update the hit/miss results in h2h_scoring table based on actual outcomes.
    Reads from betting_lines_predictions table (any model, not just h2h).
    """
    try:
        with engine.begin() as conn:
            query = text("""
                UPDATE h2h_scoring h2h
                SET
                    tiros_hit = (
                        SELECT blp.shots_hit
                        FROM betting_lines_predictions blp
                        WHERE blp.match_id = h2h.match_id
                        LIMIT 1
                    ),
                    tiros_al_arco_hit = (
                        SELECT blp.shots_on_target_hit
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
                    tarjetas_hit = (
                        SELECT blp.cards_hit
                        FROM betting_lines_predictions blp
                        WHERE blp.match_id = h2h.match_id
                        LIMIT 1
                    ),
                    faltas_hit = (
                        SELECT blp.fouls_hit
                        FROM betting_lines_predictions blp
                        WHERE blp.match_id = h2h.match_id
                        LIMIT 1
                    ),
                    updated_at = NOW()
                WHERE h2h.match_id = :match_id
            """)

            conn.execute(query, {"match_id": match_id})
            return True

    except Exception as e:
        print(f"    ⚠️  Error updating hits: {str(e)}")
        return False


def main():
    """
    Main function to populate h2h_scoring table.
    """
    print("=" * 70)
    print("🚀 POPULATING H2H SCORING TABLE")
    print("=" * 70)

    # Get command line argument for limit (optional)
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"\n📊 Processing up to {limit} matches...")
        except ValueError:
            print(f"\n⚠️  Invalid limit '{sys.argv[1]}', processing all matches")
    else:
        print("\n📊 Processing all matches with predictions...")

    # Get matches to process
    print("\n🔍 Fetching matches from database...")
    matches = get_matches_to_process(limit=limit)

    if not matches:
        print("\n❌ No matches found to process!")
        return

    print(f"\n✅ Found {len(matches)} matches to process\n")

    # Process each match
    success_count = 0
    skip_count = 0
    error_count = 0

    for i, match in enumerate(matches, 1):
        print(f"\n[{i}/{len(matches)}] Processing match {match['match_id']}: {match['league_name']} ({match['date']})")

        # Calculate and save H2H score
        if calculate_and_save_h2h_score(match):
            # Update hit/miss results
            if update_hit_results(match['match_id']):
                print(f"  ✅ Updated hit/miss results")
                success_count += 1
            else:
                skip_count += 1
        else:
            error_count += 1

    # Summary
    print("\n" + "=" * 70)
    print("📊 SUMMARY")
    print("=" * 70)
    print(f"✅ Successfully processed: {success_count}")
    print(f"⚠️  Skipped (no H2H data): {skip_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📈 Total matches: {len(matches)}")
    print("=" * 70)

    # Verify data in database
    print("\n🔍 Verifying data in h2h_scoring table...")
    with engine.begin() as conn:
        count_query = text("SELECT COUNT(*) as total FROM h2h_scoring")
        total = conn.execute(count_query).scalar()
        print(f"✅ Total rows in h2h_scoring: {total}")

        # Show sample data
        sample_query = text("""
            SELECT
                h2h.match_id,
                l.name as league,
                h2h.tiros_score,
                h2h.corners_score,
                h2h.overall_confidence
            FROM h2h_scoring h2h
            JOIN matches m ON m.id = h2h.match_id
            JOIN seasons s ON s.id = m.season_id
            JOIN leagues l ON l.id = s.league_id
            ORDER BY h2h.created_at DESC
            LIMIT 5
        """)

        samples = conn.execute(sample_query).fetchall()

        if samples:
            print("\n📋 Sample data:")
            print("-" * 70)
            for row in samples:
                print(f"  Match {row.match_id} ({row.league}): "
                      f"Tiros={row.tiros_score}, Corners={row.corners_score}, "
                      f"Confidence={row.overall_confidence}")

    print("\n✅ Done! You can now check the frontend to see the H2H effectiveness data.")


if __name__ == "__main__":
    main()
