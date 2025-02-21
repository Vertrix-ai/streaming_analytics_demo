{{ config(
    materialized='table',
    engine='SummingMergeTree()',
    order_by='minute'
) }}

SELECT 
    tumbleStart(trade_time, toIntervalMinute(1)) as minute,
    countIf(last_size > 0) as num_trades 
FROM {{ ref('stg_coinbase__trades') }}
GROUP BY minute