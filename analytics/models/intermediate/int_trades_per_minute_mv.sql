{{ config(
    materialized='clickhouse_materialized_view',
    materialization_schema='coinbase_demo',
    materialization_identifier='int_trades_per_minute',
    order_by='minute'
) }}

SELECT 
    tumbleStart(trade_time, toIntervalMinute(1)) as minute,
    SUM(last_size) as total_volume,
    SUM(last_size*price) as total_volume_price,
    countIf(last_size > 0) as num_trades 
FROM {{ ref('stg_coinbase__trades') }}
GROUP BY minute