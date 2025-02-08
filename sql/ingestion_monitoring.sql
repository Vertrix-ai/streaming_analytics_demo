-- this query shows:
--  the number of trades ingested per minute
--the volume

-- CTE for each minute since the start of the data to now
WITH time_series AS (
    SELECT 
        arrayJoin(
            range(
                toUnixTimestamp(
                    (SELECT min(tumbleStart(time, toIntervalMinute(1)))
                     FROM coinbase_demo.coinbase_ticker)
                ),
                toUnixTimestamp(
                    (SELECT max(tumbleStart(now(), toIntervalMinute(1)))
                     FROM coinbase_demo.coinbase_ticker)
                ),
                60  # increment by 60 seconds (1 minute)
            )
        ) as minute
),
-- CTE to break out the trades by minute
trade_by_minute AS (
    SELECT 
        tumbleStart(time, toIntervalMinute(1)) as minute,
        time,
        last_size,
        product_id
    FROM coinbase_demo.coinbase_ticker
)
-- select the minute and the number of rows ingested for each minute
SELECT 
    fromUnixTimestamp(ts.minute) as minute,
    countIf(t.last_size > 0 AND t.last_size IS NOT NULL) as num_rows
FROM time_series ts
LEFT JOIN trade_by_minute t ON fromUnixTimestamp(ts.minute) = t.minute
GROUP BY ts.minute
ORDER BY ts.minute DESC;
