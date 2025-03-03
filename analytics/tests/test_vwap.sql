-- This test directly builds sums values from the trades table and compares them to the vwap_5_minute_mv table
WITH trades as ( -- Get all trades
    SELECT * from {{ ref('stg_coinbase__trades') }}
),
vwap as ( -- Get all vwap values
    SELECT * from {{ ref('vwap_5_minute_mv') }}
),
totals as ( -- Get all sums of trades
    SELECT
        tumbleStart(trade_time, toIntervalMinute(5)) as minute,
        SUM(last_size) as total_volume,
        SUM(1) as num_trades
    FROM trades
    GROUP BY minute
)
-- Compare the sums of trades to the vwap values
SELECT *
FROM vwap
LEFT JOIN totals
    ON vwap.minute = totals.minute
WHERE totals.num_trades != vwap.num_trades 
  OR abs(totals.total_volume - vwap.total_volume) >= .0001