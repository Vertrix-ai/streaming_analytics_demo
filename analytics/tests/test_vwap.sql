WITH trades as (
    SELECT * from {{ ref('stg_coinbase__trades') }}
),
vwap as (
    SELECT * from {{ ref('vwap_5_minute_mv') }}
),
totals as (
    SELECT
        tumbleStart(trade_time, toIntervalMinute(5)) as minute,
        SUM(last_size) as total_volume,
        SUM(1) as num_trades
    FROM trades
    GROUP BY minute
)
SELECT *
FROM vwap
LEFT JOIN totals
    ON vwap.minute = totals.minute
WHERE totals.num_trades != vwap.num_trades 
  OR abs(totals.total_volume - vwap.total_volume) >= .0001