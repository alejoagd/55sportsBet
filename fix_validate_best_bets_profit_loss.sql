-- fix_validate_best_bets_profit_loss.sql
--
-- BUG (encontrado 2026-09-12): la función validate_best_bets() calculaba
-- profit_loss con un CASE que leía la columna `hit` — pero dentro de un mismo
-- UPDATE, Postgres evalúa cada expresión del SET contra el valor VIEJO de la
-- fila, no contra el valor que otra cláusula del mismo UPDATE acaba de
-- calcular. Como `hit` siempre es NULL antes de la primera validación,
-- `hit IS NOT NULL` daba falso en el 100% de los casos y profit_loss se
-- quedaba en NULL para siempre (la validación solo corre una vez por fila,
-- filtrando WHERE validated_at IS NULL). Efecto visible: el dashboard de
-- "Análisis de Mejores Apuestas" mostraba Ganancia/ROI en $0.00 para casi
-- todos los tipos de apuesta con cuota registrada — 117 de 121 apuestas
-- validadas con cuota real tenían profit_loss NULL en vez del valor real.
--
-- Fix: computar hit/actual_result en una subconsulta aparte y hacer JOIN
-- contra ella en el UPDATE, para que profit_loss pueda usar ese valor recién
-- calculado en la misma pasada. Los 117 registros históricos afectados ya
-- se corrigieron con un backfill puntual (profit_loss = odds-1 si hit, si no -1,
-- solo donde odds y hit ya eran correctos y profit_loss estaba en NULL).

CREATE OR REPLACE FUNCTION public.validate_best_bets(p_season_id integer DEFAULT NULL::integer)
 RETURNS TABLE(validated_count integer, hits integer, misses integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_validated INTEGER := 0;
    v_hits INTEGER := 0;
    v_misses INTEGER := 0;
BEGIN
    UPDATE best_bets_history bbh
    SET
        hit = computed.hit_value,
        actual_result = computed.actual_result_value,
        profit_loss = CASE
            WHEN bbh.odds IS NOT NULL THEN
                CASE WHEN computed.hit_value THEN (bbh.odds - 1) ELSE -1 END
            ELSE NULL
        END,
        validated_at = NOW()
    FROM (
        SELECT
            bbh2.id,
            CASE
                WHEN bbh2.bet_type = '1X2' THEN
                    CASE bbh2.prediction
                        WHEN '1' THEN m.home_goals > m.away_goals
                        WHEN 'X' THEN m.home_goals = m.away_goals
                        WHEN '2' THEN m.home_goals < m.away_goals
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'OVER_25' THEN
                    CASE
                        WHEN bbh2.prediction LIKE 'OVER%' THEN (m.home_goals + m.away_goals) > 2.5
                        WHEN bbh2.prediction LIKE 'UNDER%' THEN (m.home_goals + m.away_goals) < 2.5
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'BTTS' THEN
                    CASE bbh2.prediction
                        WHEN 'YES' THEN (m.home_goals > 0 AND m.away_goals > 0)
                        WHEN 'NO' THEN (m.home_goals = 0 OR m.away_goals = 0)
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'SHOTS' THEN
                    CASE
                        WHEN bbh2.prediction LIKE 'OVER%' THEN
                            COALESCE(ms.home_shots + ms.away_shots, 0) >
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        WHEN bbh2.prediction LIKE 'UNDER%' THEN
                            COALESCE(ms.home_shots + ms.away_shots, 0) <
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'SHOTS_ON_TARGET' THEN
                    CASE
                        WHEN bbh2.prediction LIKE 'OVER%' THEN
                            COALESCE(ms.home_shots_on_target + ms.away_shots_on_target, 0) >
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        WHEN bbh2.prediction LIKE 'UNDER%' THEN
                            COALESCE(ms.home_shots_on_target + ms.away_shots_on_target, 0) <
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'CORNERS' THEN
                    CASE
                        WHEN bbh2.prediction LIKE 'OVER%' THEN
                            COALESCE(ms.home_corners + ms.away_corners, 0) >
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        WHEN bbh2.prediction LIKE 'UNDER%' THEN
                            COALESCE(ms.home_corners + ms.away_corners, 0) <
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'CARDS' THEN
                    CASE
                        WHEN bbh2.prediction LIKE 'OVER%' THEN
                            COALESCE(ms.total_cards, 0) >
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        WHEN bbh2.prediction LIKE 'UNDER%' THEN
                            COALESCE(ms.total_cards, 0) <
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        ELSE FALSE
                    END
                WHEN bbh2.bet_type = 'FOULS' THEN
                    CASE
                        WHEN bbh2.prediction LIKE 'OVER%' THEN
                            COALESCE(ms.home_fouls + ms.away_fouls, 0) >
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        WHEN bbh2.prediction LIKE 'UNDER%' THEN
                            COALESCE(ms.home_fouls + ms.away_fouls, 0) <
                            CAST(REGEXP_REPLACE(bbh2.prediction, '[^0-9.]', '', 'g') AS NUMERIC)
                        ELSE FALSE
                    END
                ELSE FALSE
            END AS hit_value,
            CASE
                WHEN bbh2.bet_type = '1X2' THEN
                    CASE
                        WHEN m.home_goals > m.away_goals THEN '1'
                        WHEN m.home_goals = m.away_goals THEN 'X'
                        ELSE '2'
                    END
                WHEN bbh2.bet_type = 'OVER_25' THEN
                    CASE WHEN (m.home_goals + m.away_goals) > 2.5 THEN 'OVER' ELSE 'UNDER' END
                WHEN bbh2.bet_type = 'SHOTS' THEN
                    CONCAT('Total: ', COALESCE(ms.home_shots + ms.away_shots, 0))
                WHEN bbh2.bet_type = 'SHOTS_ON_TARGET' THEN
                    CONCAT('Total: ', COALESCE(ms.home_shots_on_target + ms.away_shots_on_target, 0))
                WHEN bbh2.bet_type = 'CORNERS' THEN
                    CONCAT('Total: ', COALESCE(ms.home_corners + ms.away_corners, 0))
                WHEN bbh2.bet_type = 'CARDS' THEN
                    CONCAT('Total: ', COALESCE(ms.total_cards, 0))
                WHEN bbh2.bet_type = 'FOULS' THEN
                    CONCAT('Total: ', COALESCE(ms.home_fouls + ms.away_fouls, 0))
                WHEN bbh2.bet_type = 'BTTS' THEN
                    CASE WHEN (m.home_goals > 0 AND m.away_goals > 0) THEN 'YES' ELSE 'NO' END
                ELSE 'N/A'
            END AS actual_result_value
        FROM best_bets_history bbh2
        JOIN matches m ON m.id = bbh2.match_id
        LEFT JOIN match_stats ms ON ms.match_id = m.id
        WHERE bbh2.validated_at IS NULL
          AND m.home_goals IS NOT NULL
          AND m.away_goals IS NOT NULL
          AND (p_season_id IS NULL OR bbh2.season_id = p_season_id)
    ) computed
    WHERE bbh.id = computed.id;

    GET DIAGNOSTICS v_validated = ROW_COUNT;

    SELECT
        COUNT(*) FILTER (WHERE hit = TRUE),
        COUNT(*) FILTER (WHERE hit = FALSE)
    INTO v_hits, v_misses
    FROM best_bets_history
    WHERE validated_at >= NOW() - INTERVAL '1 minute';

    RETURN QUERY SELECT v_validated, v_hits, v_misses;
END;
$function$;

-- Backfill puntual ya aplicado en producción (documentado acá para referencia,
-- no hace falta volver a correrlo salvo que se reconstruya la BD desde cero):
--
-- UPDATE best_bets_history
-- SET profit_loss = CASE WHEN hit THEN (odds - 1) ELSE -1 END
-- WHERE odds IS NOT NULL AND hit IS NOT NULL AND profit_loss IS NULL;
