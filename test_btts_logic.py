"""
Test the BTTS evaluation logic for the problematic cases.
This simulates what should happen with the fix.
"""

def test_btts_evaluation():
    print("=" * 70)
    print("BTTS EVALUATION LOGIC TEST")
    print("=" * 70)

    test_cases = [
        {
            "match": "Brentford 2-2 Wolves",
            "home_goals": 2,
            "away_goals": 2,
            "predicted_btts": "NO",
            "expected_hit": False,  # NO vs YES = MISS
            "description": "Predicted NO, but both teams scored"
        },
        {
            "match": "West Ham 1-1 Man City",
            "home_goals": 1,
            "away_goals": 1,
            "predicted_btts": "YES",
            "expected_hit": True,  # YES vs YES = HIT
            "description": "Predicted YES, both teams scored"
        },
        {
            "match": "Example: One team shutout",
            "home_goals": 2,
            "away_goals": 0,
            "predicted_btts": "NO",
            "expected_hit": True,  # NO vs NO = HIT
            "description": "Predicted NO, away team didn't score"
        },
    ]

    print("\nTesting with the FIXED logic:\n")

    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['match']}")
        print(f"  {test['description']}")
        print(f"  Final Score: {test['home_goals']}-{test['away_goals']}")

        # Calculate actual BTTS
        actual_btts = "YES" if (test['home_goals'] > 0 and test['away_goals'] > 0) else "NO"
        print(f"  Actual BTTS: {actual_btts}")

        # Simulate the FIX logic
        predicted_raw = test['predicted_btts']
        predicted_normalized = 'YES' if (predicted_raw == 'YES') else 'NO'

        print(f"  Predicted BTTS (raw): '{predicted_raw}'")
        print(f"  Predicted BTTS (normalized): '{predicted_normalized}'")

        # Calculate hit
        hit = (predicted_normalized == actual_btts)

        print(f"  Comparison: '{predicted_normalized}' == '{actual_btts}' = {hit}")
        print(f"  Expected Hit: {test['expected_hit']}")

        if hit == test['expected_hit']:
            print(f"  ✓ PASS")
        else:
            print(f"  ✗ FAIL - Got {hit} but expected {test['expected_hit']}")

        print()

    print("=" * 70)
    print("Test complete!")
    print("=" * 70)

if __name__ == "__main__":
    test_btts_evaluation()
