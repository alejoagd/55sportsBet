"""
Quick script to update hit/miss results for existing h2h_scoring records.
Run this after populate_h2h_scoring.py to fill in the NULL hit columns.
"""

from sqlalchemy import text
from src.db import engine


def main():
    print("=" * 70)
    print("🔧 FIXING H2H SCORING HIT/MISS RESULTS")
    print("=" * 70)

    with engine.begin() as conn:
        # Update all records at once
        update_query = text("""
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
            WHERE tiros_hit IS NULL
        """)

        print("\n🔄 Updating hit/miss results for all records...")
        result = conn.execute(update_query)
        updated_count = result.rowcount

        print(f"✅ Updated {updated_count} records")

        # Verify the update
        verify_query = text("""
            SELECT
                COUNT(*) as total,
                COUNT(tiros_hit) as with_tiros_hit,
                COUNT(corners_hit) as with_corners_hit
            FROM h2h_scoring
        """)

        stats = conn.execute(verify_query).fetchone()

        print("\n📊 Verification:")
        print(f"  Total records: {stats.total}")
        print(f"  Records with tiros_hit: {stats.with_tiros_hit}")
        print(f"  Records with corners_hit: {stats.with_corners_hit}")

        # Show sample
        sample_query = text("""
            SELECT
                match_id,
                tiros_score,
                tiros_hit,
                corners_score,
                corners_hit,
                overall_confidence
            FROM h2h_scoring
            WHERE tiros_hit IS NOT NULL
            LIMIT 5
        """)

        samples = conn.execute(sample_query).fetchall()

        if samples:
            print("\n📋 Sample data:")
            print("-" * 70)
            for row in samples:
                print(f"  Match {row.match_id}: "
                      f"Tiros={row.tiros_score} ({'HIT' if row.tiros_hit else 'MISS'}), "
                      f"Corners={row.corners_score} ({'HIT' if row.corners_hit else 'MISS'})")

    print("\n✅ Done! Check the frontend now - data should appear.")
    print("=" * 70)


if __name__ == "__main__":
    main()
