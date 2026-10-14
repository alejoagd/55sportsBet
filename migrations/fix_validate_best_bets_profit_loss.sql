-- fix_validate_best_bets_profit_loss.sql
--
-- BUG 1 (encontrado 2026-09-12): la función validate_best_bets() calculaba
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
-- Fix 1: computar hit/actual_result en una subconsulta aparte y hacer JOIN
-- contra ella en el UPDATE, para que profit_loss pueda usar ese valor recién
-- calculado en la misma pasada. Los 117 registros históricos afectados ya
-- se corrigieron con un backfill puntual (profit_loss = odds-1 si hit, si no -1,
-- solo donde odds y hit ya eran correctos y profit_loss estaba en NULL).
--
-- BUG 2 (encontrado el mismo día, reportado por el usuario al no entender el
-- ROI mostrado): profit_loss se calculaba como (odds-1) o -1 — es decir, en
-- base a una apuesta de $1 — pero el resto del dashboard (y el pie de página
-- "Stake fijo: $10 por cada apuesta") asumía $10 por apuesta. El % de ROI en
-- sí salía bien (es una proporción, no depende de la escala del stake), pero
-- el monto en dólares mostrado ($-10.05) no coincidía con la "Inversión"
-- mostrada al lado ($1210) — con esos números el ROI debería haber sido
-- -0.83%, no el -8.3% real. Fix 2: multiplicar por v_stake=10 al calcular
-- profit_loss, re-escalar x10 los valores ya guardados, y corregir el
-- denominador de roi_pct en /api/best-bets/stats (ROUND(100*SUM(profit_loss)
-- / (count_con_cuota * 10), 2)) para que siga siendo el % correcto ahora que
-- profit_loss está en dólares reales y no en "unidades de $1".

CREATE OR REPLACE FUNCTION public.validate_best_bets(p_season_id integer DEFAULT NULL::integer)
 RETURNS TABLE(validated_count integer, hits integer, misses integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_validated INTEGER := 0;
    v_hits INTEGER := 0;
    v_misses INTEGER := 0;
    v_stake CONSTANT NUMERIC := 10;
BEGIN
    UPDATE best_bets_history bbh
    SET
        hit = computed.hit_value,
        actual_result = computed.actual_result_value,
        profit_loss = CASE
            WHEN bbh.odds IS NOT NULL THEN
                CASE WHEN computed.hit_value THEN (bbh.odds - 1) * v_stake ELSE -v_stake END
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

-- Backfills puntuales ya aplicados en producción (documentados acá para
-- referencia, no hace falta volver a correrlos salvo que se reconstruya la
-- BD desde cero):
--
-- 1) Rellenar los profit_loss que se quedaron en NULL por el bug 1 (en base $1):
-- UPDATE best_bets_history
-- SET profit_loss = CASE WHEN hit THEN (odds - 1) ELSE -1 END
-- WHERE odds IS NOT NULL AND hit IS NOT NULL AND profit_loss IS NULL;
--
-- 2) Re-escalar todo a la base $10 real (bug 2), corrido una sola vez después del paso 1:
-- UPDATE best_bets_history
-- SET profit_loss = profit_loss * 10
-- WHERE odds IS NOT NULL AND hit IS NOT NULL AND profit_loss IS NOT NULL;
