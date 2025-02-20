{%- set materialization_table = ref('int_trades_per_minute') -%}

{{ log("Materialization table schema: " ~ materialization_table.schema, info=True) }}
{{ log("Materialization table identifier: " ~ materialization_table.identifier, info=True) }}

{{ config(
    materialized='clickhouse_materialized_view',
    materialization_s='coinbase_demo',
    materialization_i='int_trades_per_minute'
) }}

SELECT 
    tumbleStart(trade_time, toIntervalMinute(1)) as minute,
    countIf(last_size > 0) as num_trades 
FROM {{ ref('stg_coinbase__trades') }}
GROUP BY minute