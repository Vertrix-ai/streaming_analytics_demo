{{ config(
    materialized='clickhouse_materialized_view',
    materialization_schema='coinbase_demo',
    materialization_identifier='vwap_5_minute',
    order_by='minute'
) }}

WITH five_minute_intervals AS (
    SELECT 
        tumbleStart(minute, toIntervalMinute(5)) as five_min_interval
    FROM {{ ref('minutes') }}
    GROUP BY five_min_interval
)
SELECT 
    five_min_interval as minute,
    SUM(int_trades_per_minute.total_volume) as total_volume,
    SUM(int_trades_per_minute.total_volume_price) as total_volume_price,
    IF(total_volume > 0, total_volume_price/total_volume, 0) as vwap,
    SUM(int_trades_per_minute.num_trades) as num_trades 
FROM five_minute_intervals
LEFT JOIN {{ ref('int_trades_per_minute') }} as int_trades_per_minute
    ON five_minute_intervals.five_min_interval = tumbleStart(int_trades_per_minute.minute, toIntervalMinute(5))
GROUP BY minute