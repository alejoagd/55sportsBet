# Instructions to Fix BTTS Evaluation on Production

## The Problem

The automated workflow is still showing incorrect BTTS evaluations for Weinston predictions. Example:
- Brentford 2-2 Wolves: Weinston predicted "NO" for BTTS, but both teams scored (actual = YES). It should show MISS but shows HIT.

## Why The Fix Isn't Working Yet

The fix was pushed to GitHub, but you need to:
1. **Pull the latest code** on your production server
2. **Clear Python cache** to ensure the new code is used
3. **Re-run the evaluation** for the affected matches

## Steps to Fix

### Step 1: On Production Server - Pull Latest Code

```bash
cd /path/to/55sportsBet  # Your production directory
git pull origin main
```

### Step 2: Clear Python Cache

```bash
# Clear all cached Python bytecode
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
```

### Step 3: Verify the Fix is Present

```bash
grep "FIX: Use same logic" src/predictions/evaluate.py
```

You should see:
```
# ✅ FIX: Use same logic as /api/recalculate-outcomes for consistency
```

If you don't see this, the code wasn't pulled correctly.

### Step 4: Re-Evaluate the Affected Matches

Option A: Use the CLI evaluate command
```bash
python -m src.predictions.cli evaluate --season-id YOUR_SEASON_ID --from 2026-03-14 --to 2026-03-16
```

Option B: Use the Recalcular Aciertos button
- Just click the button on the frontend for that season
- This will re-evaluate ALL matches for the season using the correct logic

## Expected Result

After re-evaluation:
- Brentford 2-2 Wolves: Weinston BTTS "NO" should show ✗ (MISS) not ✓ (HIT)
- West Ham 1-1 Man City: Should remain correct if it's currently correct

## Verification

1. Check the frontend after re-evaluation
2. Matches where prediction ≠ actual should show ✗
3. Matches where prediction = actual should show ✓

## Alternative: Force Re-Evaluation via API

If you prefer, you can call the recalculate endpoint via curl:

```bash
curl -X POST "https://your-api-url.com/api/recalculate-outcomes?season_id=YOUR_SEASON_ID"
```

This will use the working `/api/recalculate-outcomes` logic which was already correct.

## Root Cause

The issue was that `src/predictions/evaluate.py` (used by automated workflow) had slightly different logic than `/api/recalculate-outcomes` (used by the button). The fix makes them identical.

The key change is that now both:
1. Force BTTS to be either "YES" or "NO" (defaults to "NO" if invalid)
2. Compare the prediction with the actual result consistently
3. Handle NULL values the same way

## Need Help?

If you still see issues after following these steps, please share:
1. The output of `grep "FIX: Use same logic" src/predictions/evaluate.py` (to confirm fix is present)
2. The output of the evaluate command showing the debug logs
3. A screenshot of the affected match after re-evaluation
