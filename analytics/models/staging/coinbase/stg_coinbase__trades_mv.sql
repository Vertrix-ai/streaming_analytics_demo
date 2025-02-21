{{ config(
    materialized='clickhouse_materialized_view',
    materialization_schema='coinbase_demo',
    materialization_identifier='stg_coinbase__trades',
    order_by='trade_time'
) }}

with source as (
    select * from coinbase_demo.coinbase_ticker
)
SELECT 
    sequence as sequence_id,
    trade_id,
    price,
    last_size,
    time as trade_time,
    product_id,
    side,
    open_24h,
    volume_24h,
    low_24h,
    high_24h,
    volume_30d,
    best_bid,
    best_ask,
    best_bid_size,
    best_ask_size
FROM source