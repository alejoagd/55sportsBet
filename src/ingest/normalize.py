import pandas as pd

SPANISH_TO_DB = {
    "1": "prob_home_win",
    "X": "prob_draw",
    "2": "prob_away_win",
    "Mas de 2,5": "over_2",
    "Menos de 2,5": "under_2",
    "Ambos Marcan": "both_score",
    "No marcan ambos": "both_Noscore",
}

def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    return df.rename(columns=SPANISH_TO_DB)