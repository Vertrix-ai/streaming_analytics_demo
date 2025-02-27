{{ config(
    materialized='table',
    engine='SummingMergeTree()',
    order_by='minute'
) }}

SELECT 
    tumbleStart(trade_time, toIntervalMinute(1)) as minute,
    SUM(last_size) as total_volume,
    SUM(last_size*price) as total_volume_price,
    countIf(last_size > 0) as num_trades 
FROM {{ ref('stg_coinbase__trades') }}
GROUP BY minute