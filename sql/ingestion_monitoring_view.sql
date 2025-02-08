
-- create a table to store the trades per minute
CREATE TABLE IF NOT EXISTS coinbase_demo.trades_per_minute
(
    minute DateTime,
    num_trades UInt64
) ENGINE = SummingMergeTree()
ORDER BY minute;

-- create a materialized view which will update the trades per minute table
CREATE MATERIALIZED VIEW IF NOT EXISTS coinbase_demo.trades_per_minute_mv
TO coinbase_demo.trades_per_minute
AS
SELECT 
    tumbleStart(time, toIntervalMinute(1)) as minute,
    countIf(last_size > 0) as num_trades
FROM coinbase_demo.coinbase_ticker
GROUP BY minute;

-- now we populate the table with the existing data
INSERT INTO coinbase_demo.trades_per_minute
SELECT 
    tumbleStart(time, toIntervalMinute(1)) as minute,
    countIf(last_size > 0) as num_trades
FROM coinbase_demo.coinbase_ticker
GROUP BY minute;

WITH time_series AS (
    SELECT 
        arrayJoin(
            range(
                toUnixTimestamp(
                    (SELECT min(minute)
                     FROM coinbase_demo.trades_per_minute)
                ),
                toUnixTimestamp(
                    (SELECT tumbleStart(now(), toIntervalMinute(1)))
                ),
                60  # increment by 60 seconds (1 minute)
            )
        ) as minute,
        0 as num_trades
),
-- We need to get the sum of the trades per minute because the 
-- SummingMergeTree delays the summing until merge time. This is 
-- done for insert performance, so the most recent minute may have
-- not been summed yet.
summed_trades AS (
    SELECT 
        minute,
        sum(num_trades) as num_trades
    FROM coinbase_demo.trades_per_minute
    GROUP BY minute
    ORDER BY minute DESC
)
-- Now we join the time series with the summed trades to get the trades
-- per minute.
SELECT 
     fromUnixTimestamp(ts.minute) as minute,
     greatest(ts.num_trades, t.num_trades) as num_trades
FROM time_series ts
LEFT JOIN coinbase_demo.trades_per_minute t ON fromUnixTimestamp(ts.minute) = t.minute
ORDER BY minute DESC;