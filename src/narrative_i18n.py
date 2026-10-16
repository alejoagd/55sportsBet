"""
Textos de la narrativa H2H (/api/matches/{id}/h2h-analysis) en los idiomas de
la app (es, en, pt, fr). El español es el idioma base y conserva exactamente
el texto que ya se generaba antes; el resto lo traduce. Las plantillas usan
str.format (con formatos como {avg:.1f}).

Los nombres de equipos no se traducen. Si llega un idioma no soportado se usa
español.
"""
from __future__ import annotations

SUPPORTED_LANGS = ("es", "en", "pt", "fr")
DEFAULT_LANG = "es"

TEXT: dict[str, dict[str, str]] = {
    "es": {
        "no_data": "No hay datos históricos disponibles para enfrentamientos entre {home} y {away}.",
        "summary": "En los últimos {n} enfrentamientos directos entre {home} y {away}, se han promediado {avg:.1f} goles por partido. ",
        "btts_high": "Ambos equipos han anotado en el {pct:.0f}% de los encuentros, mostrando una clara tendencia ofensiva. ",
        "btts_low": "Solo en el {pct:.0f}% de los partidos ambos equipos han marcado, indicando encuentros con pocos goles. ",
        "over25": "El {pct:.0f}% de los partidos han tenido más de 2.5 goles.",
        "home_header": "Cuando {home} ha jugado de local contra {away} (últimos {n} partidos):\n{home}: G{w}-E{d}-P{l} | BTTS: {b}/{n} | Over 2.5: {o}/{n}\n\n- Promedio de goles: {home} {hg:.1f} - {away} {ag:.1f}\n",
        "away_header": "Cuando {home} ha jugado de visitante contra {away} (últimos {n} partidos):\n{home}: G{w}-E{d}-P{l} | BTTS: {b}/{n} | Over 2.5: {o}/{n}\n\n- Promedio de goles: {away} {og:.1f} - {home} {tg:.1f}\n",
        "line_shots": "- Promedio de tiros: {a:.1f} del {ta} vs {b:.1f} del {tb}\n",
        "line_sot": "- Promedio de tiros al arco: {a:.1f} del {ta} vs {b:.1f} del {tb}\n",
        "line_corners": "- Promedio de corners: {a:.1f} del {ta} vs {b:.1f} del {tb}\n",
        "line_fouls": "- Promedio de faltas: {a:.1f} del {ta} vs {b:.1f} del {tb}\n",
        "line_cards": "- Promedio de tarjetas: {a:.1f} del {ta} vs {b:.1f} del {tb}\n",
        "pred_header": "Predicción para este partido:\n- Goles esperados: {h:.1f} - {a:.1f} (Total: {t:.1f})\n- Histórico: {avg:.1f} goles promedio\n\n",
        "pred_aligned": "La predicción se alinea con el histórico reciente.",
        "pred_more": "Se espera un partido con más goles que el promedio histórico (+{d:.1f} goles).",
        "pred_less": "Se espera un partido con menos goles que el promedio histórico ({d:.1f} goles).",
        "concl_intro": "Tendencia: Los enfrentamientos directos muestran ",
        "concl_high": "partidos con muchos goles",
        "concl_mid": "partidos equilibrados",
        "concl_low": "partidos cerrados y defensivos",
        "concl_extra": ", con un promedio de {c:.0f} corners y {k:.0f} tarjetas por partido.",
        "label_shots": "Tiros",
        "label_shots_on_target": "Tiros a puerta",
        "label_corners": "Corners",
        "label_fouls": "Faltas",
        "label_cards": "Tarjetas",
        "sr_no_data": 'No hay suficientes datos para analizar',
        "sr_best": '🎯 Rango óptimo: {label} (Accuracy: {acc:.1f}%, ROI: {roi:.1f}%). Se recomienda apostar cuando el score esté en este rango.',
        "sr_none": 'No hay rangos con suficiente confiabilidad (>60% accuracy)',
    },
    "en": {
        "no_data": "No historical data available for matchups between {home} and {away}.",
        "summary": "Over the last {n} head-to-head matches between {home} and {away}, an average of {avg:.1f} goals per match has been scored. ",
        "btts_high": "Both teams have scored in {pct:.0f}% of the matches, showing a clear attacking trend. ",
        "btts_low": "Both teams have scored in only {pct:.0f}% of the matches, indicating low-scoring encounters. ",
        "over25": "{pct:.0f}% of the matches have had more than 2.5 goals.",
        "home_header": "When {home} has played at home against {away} (last {n} matches):\n{home}: W{w}-D{d}-L{l} | BTTS: {b}/{n} | Over 2.5: {o}/{n}\n\n- Average goals: {home} {hg:.1f} - {away} {ag:.1f}\n",
        "away_header": "When {home} has played away against {away} (last {n} matches):\n{home}: W{w}-D{d}-L{l} | BTTS: {b}/{n} | Over 2.5: {o}/{n}\n\n- Average goals: {away} {og:.1f} - {home} {tg:.1f}\n",
        "line_shots": "- Average shots: {a:.1f} for {ta} vs {b:.1f} for {tb}\n",
        "line_sot": "- Average shots on target: {a:.1f} for {ta} vs {b:.1f} for {tb}\n",
        "line_corners": "- Average corners: {a:.1f} for {ta} vs {b:.1f} for {tb}\n",
        "line_fouls": "- Average fouls: {a:.1f} for {ta} vs {b:.1f} for {tb}\n",
        "line_cards": "- Average cards: {a:.1f} for {ta} vs {b:.1f} for {tb}\n",
        "pred_header": "Prediction for this match:\n- Expected goals: {h:.1f} - {a:.1f} (Total: {t:.1f})\n- Historical: {avg:.1f} average goals\n\n",
        "pred_aligned": "The prediction is in line with recent history.",
        "pred_more": "A match with more goals than the historical average is expected (+{d:.1f} goals).",
        "pred_less": "A match with fewer goals than the historical average is expected ({d:.1f} goals).",
        "concl_intro": "Trend: Head-to-head matches show ",
        "concl_high": "high-scoring matches",
        "concl_mid": "balanced matches",
        "concl_low": "tight, defensive matches",
        "concl_extra": ", with an average of {c:.0f} corners and {k:.0f} cards per match.",
        "label_shots": "Shots",
        "label_shots_on_target": "Shots on target",
        "label_corners": "Corners",
        "label_fouls": "Fouls",
        "label_cards": "Cards",
        "sr_no_data": 'Not enough data to analyze',
        "sr_best": '🎯 Optimal range: {label} (Accuracy: {acc:.1f}%, ROI: {roi:.1f}%). Betting is recommended when the score is in this range.',
        "sr_none": 'No ranges with enough reliability (>60% accuracy)',
    },
    "pt": {
        "no_data": "Não há dados históricos disponíveis para confrontos entre {home} e {away}.",
        "summary": "Nos últimos {n} confrontos diretos entre {home} e {away}, a média foi de {avg:.1f} gols por jogo. ",
        "btts_high": "Ambas as equipes marcaram em {pct:.0f}% dos jogos, mostrando uma clara tendência ofensiva. ",
        "btts_low": "Ambas as equipes marcaram em apenas {pct:.0f}% dos jogos, indicando partidas com poucos gols. ",
        "over25": "{pct:.0f}% dos jogos tiveram mais de 2,5 gols.",
        "home_header": "Quando {home} jogou em casa contra {away} (últimos {n} jogos):\n{home}: V{w}-E{d}-D{l} | BTTS: {b}/{n} | Over 2.5: {o}/{n}\n\n- Média de gols: {home} {hg:.1f} - {away} {ag:.1f}\n",
        "away_header": "Quando {home} jogou fora de casa contra {away} (últimos {n} jogos):\n{home}: V{w}-E{d}-D{l} | BTTS: {b}/{n} | Over 2.5: {o}/{n}\n\n- Média de gols: {away} {og:.1f} - {home} {tg:.1f}\n",
        "line_shots": "- Média de chutes: {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_sot": "- Média de chutes no alvo: {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_corners": "- Média de escanteios: {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_fouls": "- Média de faltas: {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_cards": "- Média de cartões: {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "pred_header": "Previsão para esta partida:\n- Gols esperados: {h:.1f} - {a:.1f} (Total: {t:.1f})\n- Histórico: {avg:.1f} gols em média\n\n",
        "pred_aligned": "A previsão está alinhada com o histórico recente.",
        "pred_more": "Espera-se uma partida com mais gols que a média histórica (+{d:.1f} gols).",
        "pred_less": "Espera-se uma partida com menos gols que a média histórica ({d:.1f} gols).",
        "concl_intro": "Tendência: Os confrontos diretos mostram ",
        "concl_high": "jogos com muitos gols",
        "concl_mid": "jogos equilibrados",
        "concl_low": "jogos fechados e defensivos",
        "concl_extra": ", com média de {c:.0f} escanteios e {k:.0f} cartões por jogo.",
        "label_shots": "Chutes",
        "label_shots_on_target": "Chutes no alvo",
        "label_corners": "Escanteios",
        "label_fouls": "Faltas",
        "label_cards": "Cartões",
        "sr_no_data": 'Não há dados suficientes para analisar',
        "sr_best": '🎯 Faixa ideal: {label} (Accuracy: {acc:.1f}%, ROI: {roi:.1f}%). Recomenda-se apostar quando o score estiver nesta faixa.',
        "sr_none": 'Nenhuma faixa com confiabilidade suficiente (>60% de accuracy)',
    },
    "fr": {
        "no_data": "Aucune donnée historique disponible pour les confrontations entre {home} et {away}.",
        "summary": "Lors des {n} derniers face-à-face entre {home} et {away}, la moyenne a été de {avg:.1f} buts par match. ",
        "btts_high": "Les deux équipes ont marqué dans {pct:.0f} % des rencontres, ce qui montre une nette tendance offensive. ",
        "btts_low": "Les deux équipes n'ont marqué que dans {pct:.0f} % des matchs, ce qui indique des rencontres avec peu de buts. ",
        "over25": "{pct:.0f} % des matchs ont compté plus de 2,5 buts.",
        "home_header": "Quand {home} a joué à domicile contre {away} ({n} derniers matchs) :\n{home} : G{w}-N{d}-P{l} | BTTS : {b}/{n} | Over 2.5 : {o}/{n}\n\n- Moyenne de buts : {home} {hg:.1f} - {away} {ag:.1f}\n",
        "away_header": "Quand {home} a joué à l'extérieur contre {away} ({n} derniers matchs) :\n{home} : G{w}-N{d}-P{l} | BTTS : {b}/{n} | Over 2.5 : {o}/{n}\n\n- Moyenne de buts : {away} {og:.1f} - {home} {tg:.1f}\n",
        "line_shots": "- Moyenne de tirs : {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_sot": "- Moyenne de tirs cadrés : {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_corners": "- Moyenne de corners : {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_fouls": "- Moyenne de fautes : {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "line_cards": "- Moyenne de cartons : {a:.1f} ({ta}) vs {b:.1f} ({tb})\n",
        "pred_header": "Pronostic pour ce match :\n- Buts attendus : {h:.1f} - {a:.1f} (Total : {t:.1f})\n- Historique : {avg:.1f} buts en moyenne\n\n",
        "pred_aligned": "Le pronostic est cohérent avec l'historique récent.",
        "pred_more": "On s'attend à un match avec plus de buts que la moyenne historique (+{d:.1f} buts).",
        "pred_less": "On s'attend à un match avec moins de buts que la moyenne historique ({d:.1f} buts).",
        "concl_intro": "Tendance : Les confrontations directes montrent ",
        "concl_high": "des matchs avec beaucoup de buts",
        "concl_mid": "des matchs équilibrés",
        "concl_low": "des matchs fermés et défensifs",
        "concl_extra": ", avec en moyenne {c:.0f} corners et {k:.0f} cartons par match.",
        "label_shots": "Tirs",
        "label_shots_on_target": "Tirs cadrés",
        "label_corners": "Corners",
        "label_fouls": "Fautes",
        "label_cards": "Cartons",
        "sr_no_data": 'Pas assez de données à analyser',
        "sr_best": '🎯 Tranche optimale : {label} (Accuracy : {acc:.1f} %, ROI : {roi:.1f} %). Il est recommandé de parier lorsque le score se situe dans cette tranche.',
        "sr_none": "Aucune tranche suffisamment fiable (>60 % d'accuracy)",
    },
}


def norm_lang(lang: str | None) -> str:
    """Idioma soportado (es/en/pt/fr); cualquier otro valor cae a español."""
    code = (lang or "").strip().lower().split("-")[0]
    return code if code in SUPPORTED_LANGS else DEFAULT_LANG


def tr(lang: str, key: str, **kwargs) -> str:
    return TEXT[norm_lang(lang)][key].format(**kwargs)
