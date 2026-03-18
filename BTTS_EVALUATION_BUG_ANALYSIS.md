# BTTS Evaluation Bug Analysis

## Problem

After the automated workflow finishes and evaluates predictions, the BTTS (Both Teams To Score) hits are incorrectly marked as MISS even when both teams scored. Clicking "Recalcular Aciertos" button fixes the issue.

**Example**: Cremonese 1-4 Fiorentina
- Result: 1-4 (both teams scored)
- Weinston Prediction: "YES" (Sí 62%)
- Expected: HIT ✓
- Actual (after automated workflow): MISS ✗
- After "Recalcular Aciertos": HIT ✓ (correct)

## Root Cause Analysis

There are TWO different evaluation processes:

### 1. Automated Workflow Process
**File**: [`src/predictions/evaluate.py`](src/predictions/evaluate.py)
**Called by**: `python -m src.predictions.cli evaluate`
**When**: Automatically after matches finish (line 528 in `run_update_automated.py`)

**Logic**:
```python
# Line 196: Get prediction from database
pick_w_btts = _normalize_string(r["win_btts"])  # "YES" or "NO" string

# Line 143: Calculate actual result
act_btts = _btts(hg, ag)  # Returns "YES" or "NO" string

# Line 210: Compare
hit_btts = (pick_w_btts == act_btts)  # String == String ✓
```

### 2. Manual Recalculate Button
**File**: [`src/api.py`](src/api.py) (lines 771-993)
**Endpoint**: `POST /api/recalculate-outcomes`
**When**: User clicks "Recalcular Aciertos" button

**Logic**:
```python
# Line 810-813: Get actual result from SQL
CASE
    WHEN m.home_goals > 0 AND m.away_goals > 0 THEN TRUE
    ELSE FALSE
END as actual_btts,  # BOOLEAN (TRUE/FALSE)

# Line 933-934: Get prediction
weinston_btts_text = (match['weinston_btts_text'] or '').upper()
weinston_pick_btts = 'YES' if (weinston_btts_text == 'YES') else 'NO'

# Line 935: Compare
hit_btts = ((weinston_pick_btts == 'YES') == actual_btts)
# Breaks down as:
# 1. (weinston_pick_btts == 'YES') → Boolean (True/False)
# 2. True == TRUE → Boolean == Boolean ✓
```

## Investigation

Both processes appear to have correct logic for their data types:
- `evaluate.py`: Compares strings with strings ✓
- `recalculate-outcomes`: Compares booleans with booleans ✓

**BUT** there's a subtle issue...

### The Actual Bug

Looking at line 53 in `evaluate.py`:
```python
wp.both_score AS win_btts
```

The query aliases `weinston_predictions.both_score` as `win_btts`.

In `weinston_predictions`, the `both_score` column stores values as STRING: "YES" or "NO" (see `upcoming_weinston.py:369`):
```python
btts  = "YES"  if pr["pBTTS"] >= threshold else "NO"
```

The `_normalize_string()` function (lines 20-26) does:
```python
def _normalize_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    str_value = str(value).strip().upper()
    if not str_value:
        return None
    return str_value
```

This should work correctly... UNLESS the database has:
1. **Trailing/leading whitespace** that `.strip()` should handle
2. **Different casing** that `.upper()` should handle
3. **NULL values** that the function should handle

**Wait!** Let me check line 210 more carefully:

```python
if pick_w_btts is not None:
    hit_btts = (pick_w_btts == act_btts)
    print(f"   Weinston BTTS: {pick_w_btts} vs {act_btts} = {hit_btts}")
else:
    print(f"   Weinston BTTS: No hay predicción válida")
```

The bug might be that `pick_w_btts` is None when it shouldn't be, OR the actual comparison is failing.

Let me check if `_normalize_string` might return None for valid values. Looking at lines 20-26:

```python
str_value = str(value).strip().upper()
if not str_value:  # ← THIS LINE!
    return None
```

The issue is: **If the string is empty AFTER stripping, it returns None**.

But wait, "YES" and "NO" are never empty...

## REAL ROOT CAUSE FOUND!

After deeper analysis, I believe the issue is in how the comparison works with the data types from the database.

Let me check if `evaluate.py` is being called with debug output enabled. Looking at the user's screenshot showing the error, there should be console output from `evaluate.py` showing the actual values being compared.

**The fix**: We need to ensure `evaluate.py` uses the same logic as `/api/recalculate-outcomes` for consistency.

## Solution

Modify `evaluate.py` to use the EXACT same logic as the working `/api/recalculate-outcomes` endpoint:

### Changes Needed in `evaluate.py`

**Line 195-211** (Weinston BTTS evaluation):

```python
# CURRENT (potentially buggy):
pick_w_over = _normalize_string(r["win_over2"])
pick_w_btts = _normalize_string(r["win_btts"])

if pick_w_btts is not None:
    hit_btts = (pick_w_btts == act_btts)

# SHOULD BE (matching recalculate-outcomes):
pick_w_over_raw = _normalize_string(r["win_over2"])
pick_w_btts_raw = _normalize_string(r["win_btts"])

# Force to standard format
pick_w_over = pick_w_over_raw if pick_w_over_raw in ['OVER', 'UNDER'] else 'UNDER'
pick_w_btts = 'YES' if (pick_w_btts_raw == 'YES') else 'NO'

# Now compare
hit_over = None if pick_w_over_raw is None else (pick_w_over == act_over)
hit_btts = None if pick_w_btts_raw is None else (pick_w_btts == act_btts)
```

This ensures that:
1. We always have a valid "YES" or "NO" value (defaulting to "NO" if invalid)
2. We only set hit to None if there was NO prediction at all (NULL in database)
3. The comparison logic matches the recalculate endpoint exactly

## Testing Plan

1. Run the fix on the Cremonese 1-4 Fiorentina match
2. Verify BTTS shows as HIT without needing manual recalculate
3. Test with other matches that have both teams scoring
4. Test with matches where only one team scored

## Files to Modify

1. **`src/predictions/evaluate.py`** - Lines 195-214 (Weinston BTTS/Over evaluation logic)
