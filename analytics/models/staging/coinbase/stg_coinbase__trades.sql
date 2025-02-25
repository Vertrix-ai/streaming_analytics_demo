/*
    Model representing the coinbase tick data, slightly renamed.
*/
{{ config(
    materialized='table',
    engine='MergeTree()',
    order_by='trade_time'
) }}

with source as (
    select * from {{ source('stg_coinbase__sources', 'coinbase_ticker') }}
)
select 
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
from source
