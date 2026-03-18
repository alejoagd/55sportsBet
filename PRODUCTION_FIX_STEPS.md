# Production Fix Steps - BTTS Evaluation Bug

## Quick Summary

The fix has been pushed to GitHub. You need to deploy it to production.

## On Your Production Server

### 1. Navigate to project directory
```bash
cd /path/to/your/production/55sportsBet
```

### 2. Pull latest code
```bash
git pull origin main
```

Expected output:
```
remote: Enumerating objects: X, done.
...
Updating 2137554..17f2bff
Fast-forward
 BTTS_EVALUATION_BUG_ANALYSIS.md |  186 +++++++++++++++++++
 src/predictions/evaluate.py     |   18 +-
 2 files changed, 194 insertions(+), 10 deletions(-)
```

### 3. Verify the fix is present
```bash
cat src/predictions/evaluate.py | grep -A 5 "FIX: Use same logic"
```

Should show:
```python
# ✅ FIX: Use same logic as /api/recalculate-outcomes for consistency
pick_w_over_raw = _normalize_string(r["win_over2"])
pick_w_btts_raw = _normalize_string(r["win_btts"])

# Ensure valid values (matching recalculate-outcomes logic)
pick_w_over = pick_w_over_raw if pick_w_over_raw in ['OVER', 'UNDER'] else 'UNDER'
```

### 4. Clear Python cache (IMPORTANT!)
```bash
find . -type d -name "__pycache__" | xargs rm -rf
find . -name "*.pyc" | xargs rm -f
```

### 5. Re-evaluate the matches

**Option A: Re-run evaluation for specific date range**
```bash
# For Serie A (season_id might be different)
python -m src.predictions.cli evaluate --season-id 5 --from 2026-03-14 --to 2026-03-16

# Or for all leagues that had matches in that range
python src/scripts/run_update_automated.py --mode finish --date-from 2026-03-14 --date-to 2026-03-16 --leagues all --env-file .env.production
```

**Option B: Use the "Recalcular Aciertos" button**
- Go to your website
- Click "Recalcular Aciertos" button
- This will re-evaluate ALL matches using the correct API endpoint

## Expected Results After Re-Evaluation

### Brentford 2-2 Wolves (March 16, 2026)
- Result: 2-2 (both teams scored)
- **Poisson BTTS**: Predicted NO, Actual YES → Should show ✗ (MISS) ← Already correct
- **Weinston BTTS**: Predicted NO, Actual YES → Should show ✗ (MISS) ← Will be FIXED

### West Ham 1-1 Man City (March 14, 2026)
- Result: 1-1 (both teams scored)
- **Poisson BTTS**: If predicted YES, should show ✓ (HIT)
- **Weinston BTTS**: If predicted YES, should show ✓ (HIT)

## Troubleshooting

### If fix is still not working after re-evaluation:

1. **Check if code was pulled correctly:**
```bash
git log -1 --oneline
```
Should show: `17f2bff Fix BTTS evaluation bug in automated workflow`

2. **Check if you're using a virtual environment:**
```bash
which python
# Make sure it's pointing to your project's virtual environment
```

3. **Restart your API server** (if using gunicorn/uvicorn):
```bash
# Find the process
ps aux | grep uvicorn

# Kill and restart
sudo systemctl restart your-api-service
```

4. **Check the evaluation logs** when running evaluate command:
The output should show:
```
Weinston raw: over='OVER', btts='NO'
Weinston normalized: over='OVER', btts='NO'
```

## Still Having Issues?

If after following all these steps you still see incorrect evaluations:

1. Share the output of: `git log -1`
2. Share the output of: `grep -A 10 "FIX: Use same logic" src/predictions/evaluate.py`
3. Share the console output when running the evaluate command
4. Share a screenshot of the match after re-evaluation

This will help diagnose if there's another issue.
