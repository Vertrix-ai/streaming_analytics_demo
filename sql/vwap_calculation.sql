-- construct a series of 5 minute periods for the prior 24 hours
-- which is the period we want to chart
WITH time_series AS (
    SELECT 
        arrayJoin(
            range(
                toUnixTimestamp(
                    (SELECT tumbleStart((now() - INTERVAL 24 HOUR), toIntervalMinute(5)))
                ),
                toUnixTimestamp(
                    (SELECT tumbleStart(now(), toIntervalMinute(5)))
                ),
                300  # increment by 300 seconds (5 minutes)
            )
        ) as interval
),
-- calculate the components of the vwap
vwap AS (
    SELECT 
        tumbleStart(time, toIntervalMinute(5)) as period,
        SUM(price * last_size) as volume_price,
        SUM(last_size) as total_volume
      FROM coinbase_demo.coinbase_ticker
      WHERE 
          period >= now() - INTERVAL 24 HOUR
          AND last_size > 0  -- Filter out zero volume trades
          AND price > 0      -- Filter out invalid prices
      GROUP BY period
)
-- join the vwap calculation to the time series to give the 5 minute vwap for the last 24 hours
SELECT 
    fromUnixTimestamp(interval) as vwap_period,
    IF(v.total_volume > 0, v.volume_price/v.total_volume, 0) as vwap
FROM time_series ts
LEFT JOIN vwap v ON fromUnixTimestamp(ts.interval) = v.period
ORDER BY vwap_period DESC;