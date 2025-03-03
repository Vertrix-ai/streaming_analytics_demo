{{ config(
    materialized='table',
    engine='SummingMergeTree()',
    order_by='minute'
) }}

-- Construct 5 minute intervals
WITH five_minute_intervals AS (
    SELECT 
        tumbleStart(minute, toIntervalMinute(5)) as five_min_interval
    FROM {{ ref('minutes') }}
    GROUP BY five_min_interval
)
-- Get all vwap values
SELECT 
    five_min_interval as minute,
    SUM(total_volume) as total_volume,
    SUM(total_volume_price) as total_volume_price,
    IF(total_volume > 0, total_volume_price/total_volume, 0) as vwap,
    SUM(num_trades) as num_trades  
FROM five_minute_intervals
LEFT JOIN {{ ref('int_trades_per_minute') }} as int_trades_per_minute
    ON five_minute_intervals.five_min_interval = tumbleStart(int_trades_per_minute.minute, toIntervalMinute(5))
GROUP BY minute