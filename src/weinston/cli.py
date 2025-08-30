import typer
from sqlalchemy import text
from src.db import SessionLocal
from scipy.stats import poisson
from decimal import Decimal
from src.models import Match

app = typer.Typer(help="Weinston → weinston_predictions")

def _f(x):
    if x is None:
        return None
    if isinstance(x, Decimal):
        return float(x)
    return float(x)

def probs(lh: float, la: float, maxg: int = 10):
    """Devuelve: ph, pd, pa, over, under, yes_btts, no_btts"""
    ph = pd = pa = 0.0
    over = under = 0.0
    yy = nn = 0.0

    lh = float(lh)
    la = float(la)

    for hg in range(0, maxg + 1):
        phg = poisson.pmf(hg, lh)
        for ag in range(0, maxg + 1):
            pag = poisson.pmf(ag, la)
            p = float(phg * pag)

            # 1X2
            if hg > ag:
                ph += p
            elif hg == ag:
                pd += p
            else:
                pa += p

            # Over/Under 2.5
            if hg + ag > 2:
                over += p
            else:
                under += p

            # BTTS
            if hg > 0 and ag > 0:
                yy += p
            else:
                nn += p

    return ph, pd, pa, over, under, yy, nn

def _team_baselines(s, season_id: int):
    Q = """
    with base as (
      select m.season_id, m.home_team_id as team_id, 1 as is_home,
             m.home_goals g_for, ms.home_shots shots_for, ms.home_shots_on_target sot_for,
             ms.home_fouls fouls_for, ms.home_corners corn_for,
             ms.home_yellow_cards + coalesce(ms.home_red_cards,0) cards_for
      from matches m left join match_stats ms on ms.match_id=m.id
      where m.season_id=:sid
      union all
      select m.season_id, m.away_team_id, 0,
             m.away_goals, ms.away_shots, ms.away_shots_on_target,
             ms.away_fouls, ms.away_corners,
             ms.away_yellow_cards + coalesce(ms.away_red_cards,0)
      from matches m left join match_stats ms on ms.match_id=m.id
      where m.season_id=:sid
    )
    select team_id,is_home, avg(g_for) g_for_pg,
           avg(shots_for) shots_pg, avg(sot_for) sot_pg,
           avg(fouls_for) fouls_pg, avg(corn_for) corn_pg,
           avg(cards_for) cards_pg
    from base group by team_id,is_home
    """
    rows = s.execute(text(Q), {"sid":season_id}).mappings().all()
    return {(r["team_id"], int(r["is_home"])): r for r in rows}

def _scale(base, lam, gpg):
    if base is None or gpg in (None,0): return base
    fac = max(0.5, min(1.6, lam/float(gpg)))
    return float(base)*fac

@app.command()
def fit(season_id: int):
    """Ajusta ratings y guarda en weinston_ratings / weinston_params."""
    from src.db import SessionLocal
    from src.weinston.fit import fit_weinston
    with SessionLocal() as s:
        fr = fit_weinston(s, season_id)
        s.execute(text("delete from weinston_ratings where season_id=:sid"), {"sid":season_id})
        s.execute(text("delete from weinston_params  where season_id=:sid"), {"sid":season_id})
        rows = [{"season_id":season_id,"team_id":tid,
                 "atk_home":fr.atk_home[i],"def_home":fr.def_home[i],
                 "atk_away":fr.atk_away[i],"def_away":fr.def_away[i]}
                for i,tid in enumerate(fr.team_ids)]
        s.execute(text("""
           insert into weinston_ratings(season_id,team_id,atk_home,def_home,atk_away,def_away)
           values (:season_id,:team_id,:atk_home,:def_home,:atk_away,:def_away)
        """), rows)
        s.execute(text("""
           insert into weinston_params(season_id,mu_home,mu_away,home_adv,loss)
           values (:sid,:mh,:ma,:ha,:loss)
        """), {"sid":season_id,"mh":fr.mu_home,"ma":fr.mu_away,"ha":fr.home_adv,"loss":fr.loss})
        s.commit()
        typer.echo(f"OK fit season={season_id} loss={fr.loss:.2f}")

@app.command()
def backfill(season_id: int, only_missing: bool = typer.Option(True, "--only-missing/--no-only-missing")):
    """ 
    Escribe/actualiza la tabla weinston_predictions para la temporada dada.
    Requiere que antes hayas ejecutado: `python -m src.weinston.cli fit SEASON_ID`.
    """
    def _f(v):
        # convierte Decimal/None a float/None de forma segura
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            return float(v)

    # proyección lineal de métricas dado el promedio de goles por partido del equipo
    def _scale(x_pg: float | None, lam: float, g_for_pg: float | None) -> float | None:
        if x_pg is None or g_for_pg is None or g_for_pg == 0:
            return None
        return float(x_pg) * float(lam) / float(g_for_pg)

    with SessionLocal() as s:
        # 1) parámetros globales (mu_home, mu_away, home_adv) de esta temporada
        p = (
            s.execute(
                text(
                    """
                    select mu_home, mu_away, home_adv
                    from weinston_params
                    where season_id=:sid
                    """
                ),
                {"sid": season_id},
            )
            .mappings()
            .first()
        )
        if not p:
            raise typer.BadParameter("Primero ejecuta: python -m src.weinston.cli fit SEASON_ID")

        mh, ma, ha = _f(p["mu_home"]), _f(p["mu_away"]), _f(p["home_adv"])

        # 2) ratings por equipo (ya optimizados por el solver)
        r_rows = (
            s.execute(
                text(
                    """
                    select team_id, atk_home, def_home, atk_away, def_away
                    from weinston_ratings
                    where season_id=:sid
                    """
                ),
                {"sid": season_id},
            )
            .mappings()
            .all()
        )

        R: dict[int, dict[str, float]] = {}
        for rr in r_rows:
            R[int(rr["team_id"])] = {
                "atk_home": _f(rr["atk_home"]),
                "def_home": _f(rr["def_home"]),
                "atk_away": _f(rr["atk_away"]),
                "def_away": _f(rr["def_away"]),
            }

        # 3) baseline por equipo (promedios por partido para escalar métricas)
        bl_rows = (
            s.execute(
                text(
                    """
                    select team_id, g_for_pg, shots_pg, sot_pg, fouls_pg, corn_pg, cards_pg
                    from weinston_baseline_all
                    where season_id=:sid
                    """
                ),
                {"sid": season_id},
            )
            .mappings()
            .all()
        )

        BL: dict[int, dict[str, float]] = {}
        for b in bl_rows:
            BL[int(b["team_id"])] = {
                "g_for_pg": _f(b["g_for_pg"]),
                "shots_pg": _f(b["shots_pg"]),
                "sot_pg": _f(b["sot_pg"]),
                "fouls_pg": _f(b["fouls_pg"]),
                "corn_pg": _f(b["corn_pg"]),
                "cards_pg": _f(b["cards_pg"]),
            }

        # 4) partidos de la temporada (opcionalmente solo los que no tienen predicción)
        q = (
            s.query(
                Match.id,
                Match.home_team_id,
                Match.away_team_id,
                Match.home_goals,
                Match.away_goals,
            )
            .filter(Match.season_id == season_id)
        )
        if only_missing:
            q = q.filter(text("not exists (select 1 from weinston_predictions wp where wp.match_id = matches.id)"))

        rows = q.all()
        n = 0

        for mid, ht, at, hg, ag in rows:
            # si falta algún rating, salta el partido
            if ht not in R or at not in R:
                continue

            # 5) intensidades λ (local/visita)
            lam_h = mh * R[ht]["atk_home"] * R[at]["def_away"] * ha
            lam_a = ma * R[at]["atk_away"] * R[ht]["def_home"]

            # 6) probabilidades con Poisson
            ph, pd, pa, ov, un, yy, nn = probs(float(lam_h), float(lam_a))

            # 7) etiquetas cualitativas
            r1x2 = "1" if (ph > pd and ph > pa) else ("X" if pd > pa else "2")
            ov2 = "Mas de 2,5" if ov >= 0.5 else "Menos de 2,5"
            btts = "Ambos Marcan" if yy >= 0.5 else "No marcan ambos"

            # 8) error (si hay marcador real)
            err = (
                None
                if (hg is None or ag is None)
                else (float(hg) - float(lam_h)) ** 2 + (float(ag) - float(lam_a)) ** 2
            )

            # 9) proyección de métricas usando baseline (escala lineal por goles)
            hb, ab = BL.get(ht, {}), BL.get(at, {})
            sh = _scale(hb.get("shots_pg"), lam_h, hb.get("g_for_pg"))
            sa = _scale(ab.get("shots_pg"), lam_a, ab.get("g_for_pg"))
            soth = _scale(hb.get("sot_pg"), lam_h, hb.get("g_for_pg"))
            sota = _scale(ab.get("sot_pg"), lam_a, ab.get("g_for_pg"))
            fh = _scale(hb.get("fouls_pg"), lam_h, hb.get("g_for_pg"))
            fa = _scale(ab.get("fouls_pg"), lam_a, ab.get("g_for_pg"))
            ch = _scale(hb.get("cards_pg"), lam_h, hb.get("g_for_pg"))
            ca = _scale(ab.get("cards_pg"), lam_a, ab.get("g_for_pg"))
            coh = _scale(hb.get("corn_pg"), lam_h, hb.get("g_for_pg"))
            coa = _scale(ab.get("corn_pg"), lam_a, ab.get("g_for_pg"))

            wco = (
                "home"
                if (coh or 0) > (coa or 0)
                else ("away" if (coa or 0) > (coh or 0) else "tie")
            )

            # 10) UPSERT en weinston_predictions
            s.execute(
                text(
                    """
                    insert into weinston_predictions (
                        match_id, local_goals, away_goals, error, result_1x2, over_2, both_score,
                        shots_home, shots_away, shots_target_home, shots_target_away,
                        fouls_home, fouls_away, cards_home, cards_away,
                        corners_home, corners_away, win_corners
                    )
                    values (
                        :mid, :lh, :la, :err, :r1x2, :ov2, :btts,
                        :sh, :sa, :soth, :sota,
                        :fh, :fa, :ch, :ca,
                        :coh, :coa, :wco
                    )
                    on conflict (match_id) do update set
                        local_goals=excluded.local_goals,
                        away_goals=excluded.away_goals,
                        error=excluded.error,
                        result_1x2=excluded.result_1x2,
                        over_2=excluded.over_2,
                        both_score=excluded.both_score,
                        shots_home=excluded.shots_home,
                        shots_away=excluded.shots_away,
                        shots_target_home=excluded.shots_target_home,
                        shots_target_away=excluded.shots_target_away,
                        fouls_home=excluded.fouls_home,
                        fouls_away=excluded.fouls_away,
                        cards_home=excluded.cards_home,
                        cards_away=excluded.cards_away,
                        corners_home=excluded.corners_home,
                        corners_away=excluded.corners_away,
                        win_corners=excluded.win_corners
                    """
                ),
                {
                    "mid": mid,
                    "lh": float(lam_h),
                    "la": float(lam_a),
                    "err": err,
                    "r1x2": r1x2,
                    "ov2": ov2,
                    "btts": btts,
                    "sh": sh, "sa": sa, "soth": soth, "sota": sota,
                    "fh": fh, "fa": fa, "ch": ch, "ca": ca,
                    "coh": coh, "coa": coa, "wco": wco,
                },
            )
            n += 1

        s.commit()
        typer.echo(f"OK Weinston ⇒ weinston_predictions: {n} filas")

if __name__ == "__main__":
    #debug opcional
    print("weinston CLI __main__")
    app()

