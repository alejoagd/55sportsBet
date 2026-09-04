"""
backfill_team_logos_top5.py
Backfill de logo_url para los equipos de las 4 ligas europeas originales
(Premier League, La Liga, Serie A, Bundesliga) — a diferencia de las 5
competencias nuevas (Liga Argentina, Betplay, Brasileirao, Libertadores,
Sudamericana), estas se cargaron originalmente vía CSV/API-Football sin
logo_url, y sus nombres de equipo vienen abreviados al estilo
football-data.co.uk ("Ath Madrid", "Sociedad", "Vallecano", "Sp Gijon"),
que NO calzan por nombre exacto contra el `displayName` completo de ESPN
("Atlético Madrid", "Real Sociedad", "Rayo Vallecano", "Sporting Gijón").

Por eso este script NUNCA usa TeamResolver.resolve() (que crearía un
equipo nuevo ante cualquier nombre que no calce exacto, duplicando el
club). En su lugar:
  1. Baja la lista de equipos vigentes de cada liga desde ESPN (nombre +
     escudo) escaneando el scoreboard de la temporada.
  2. Para cada equipo ya existente en la BD sin logo_url, calcula el mejor
     candidato por solapamiento de tokens (alias de abreviaturas comunes
     incluido) y un puntaje de confianza.
  3. Por defecto solo IMPRIME el reporte (dry-run) — no escribe nada.
     Con --apply escribe logo_url, pero SOLO para los matches con
     score >= --min-score (default 0.6); todo lo demás queda listado bajo
     "revisar a mano" para no arriesgar pisar el equipo equivocado.

Uso:
  python backfill_team_logos_top5.py                # dry-run, reporte completo (llama a ESPN en vivo)
  python backfill_team_logos_top5.py --apply         # aplica solo score >= 0.6
  python backfill_team_logos_top5.py --apply --min-score 0.8

  # Si no hay salida directa a ESPN desde donde se corre esto (ver
  # scripts/fetch_espn_team_logos.py, pensado para correr en GitHub
  # Actions y bajar el resultado como artifact):
  python backfill_team_logos_top5.py --from-json data/espn_team_logos.json --apply
"""
from __future__ import annotations
import argparse
import json
import re
import unicodedata
from datetime import date, timedelta

from sqlalchemy import text

from src.db import engine
from src.ingest.espn_competition_client import fetch_scoreboard_range
from src.ingest.db_retry import run_with_retry

LEAGUES = [
    {"league_id": 1, "name": "Premier League", "espn_slug": "eng.1"},
    {"league_id": 2, "name": "La Liga", "espn_slug": "esp.1"},
    {"league_id": 3, "name": "Serie A", "espn_slug": "ita.1"},
    {"league_id": 4, "name": "Bundesliga", "espn_slug": "ger.1"},
]

# Alias de abreviaturas comunes -> forma completa, para que el solapamiento
# de tokens funcione entre nuestros nombres (estilo football-data.co.uk) y
# los displayName completos de ESPN.
ALIASES = {
    "ath": "athletic atletico",
    "sp": "sporting",
    "dep": "deportivo",
    "utd": "united",
    "man": "manchester",
    "int": "internazionale inter",
    "rc": "racing real club",
    "rcd": "real club deportivo",
    "cf": "", "fc": "", "cd": "", "sd": "", "ud": "", "ac": "", "afc": "",
    "ssc": "", "calcio": "", "1899": "", "1904": "", "1909": "", "1913": "",
    "1919": "", "club": "",
}

STOPWORDS = {"de", "la", "el", "und", "von"}


def _tokens(name: str) -> set[str]:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = re.sub(r"[^a-zA-Z0-9\s]", " ", n).lower()
    out: set[str] = set()
    for tok in n.split():
        if tok in STOPWORDS:
            continue
        expanded = ALIASES.get(tok, tok)
        for sub in expanded.split():
            out.add(sub)
    return out


def _score(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    inter = ta & tb
    union = ta | tb
    return len(inter) / len(union)


def _best_match(db_name: str, espn_teams: list[dict]) -> tuple[dict | None, float]:
    best, best_score = None, 0.0
    for et in espn_teams:
        s = _score(db_name, et["name"])
        if s > best_score:
            best, best_score = et, s
    return best, best_score


def _fetch_espn_teams(slug: str) -> list[dict]:
    """Escanea el scoreboard de la temporada y devuelve equipos distintos vistos (id/nombre/logo)."""
    start = date.today() - timedelta(days=60)
    end = date.today() + timedelta(days=30)
    fixtures = fetch_scoreboard_range(slug, start, end)

    seen: dict[int, dict] = {}
    for fx in fixtures:
        for prefix in ("home", "away"):
            eid = fx[f"{prefix}_espn_id"]
            if eid not in seen:
                seen[eid] = {"espn_id": eid, "name": fx[f"{prefix}_name"], "logo": fx.get(f"{prefix}_logo")}
    return list(seen.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill de escudos para las 4 ligas europeas originales")
    parser.add_argument("--apply", action="store_true", help="Escribe logo_url (si no se pasa, solo imprime el reporte)")
    parser.add_argument("--min-score", type=float, default=0.6, help="Puntaje mínimo de confianza para aplicar (default 0.6)")
    parser.add_argument("--from-json", help="Leer equipos+escudos desde un JSON pre-descargado (scripts/fetch_espn_team_logos.py) en vez de llamar a ESPN en vivo")
    args = parser.parse_args()

    json_data = None
    if args.from_json:
        with open(args.from_json, encoding="utf-8") as f:
            json_data = json.load(f)

    for league in LEAGUES:
        print(f"\n{'='*70}\n  {league['name']} (slug={league['espn_slug']})\n{'='*70}")

        if json_data is not None:
            espn_teams = json_data.get(str(league["league_id"]), [])
        else:
            espn_teams = run_with_retry(lambda: _fetch_espn_teams(league["espn_slug"]))
        print(f"   {len(espn_teams)} equipos vistos en ESPN")

        with engine.begin() as conn:
            db_teams = conn.execute(
                text("SELECT id, name FROM teams WHERE league_id = :lid AND logo_url IS NULL ORDER BY name"),
                {"lid": league["league_id"]},
            ).fetchall()

        applied = skipped = 0
        for t in db_teams:
            match, score = _best_match(t.name, espn_teams)
            if match is None:
                print(f"   ❌ {t.name:<35} sin candidato en ESPN")
                skipped += 1
                continue

            flag = "✅" if score >= args.min_score else "⚠️  REVISAR"
            print(f"   {flag} {t.name:<35} -> {match['name']:<35} (score={score:.2f})  {match['logo']}")

            if args.apply and score >= args.min_score:
                with engine.begin() as conn:
                    conn.execute(
                        text("UPDATE teams SET logo_url = :logo WHERE id = :tid"),
                        {"logo": match["logo"], "tid": t.id},
                    )
                applied += 1
            else:
                skipped += 1

        if args.apply:
            print(f"   -> {applied} actualizados, {skipped} sin aplicar (revisar a mano o subir --min-score)")

    print(f"\n{'='*70}")
    if not args.apply:
        print("  DRY-RUN — nada se escribió. Revisar el reporte y correr con --apply cuando esté OK.")
    print("  Listo")
    print("=" * 70)


if __name__ == "__main__":
    main()
