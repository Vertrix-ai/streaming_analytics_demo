{{ config(
    materialized='ephemeral',
    order_by='minute'
) }}

WITH trades AS (
    SELECT * from {{ ref('stg_coinbase__trades') }}
)
SELECT
    toDateTime(
        arrayJoin(
            range(
                toUnixTimestamp(
                    (SELECT tumbleStart(min(trade_time), toIntervalMinute(1))
                        FROM trades)
                ),
                toUnixTimestamp(
                    (SELECT tumbleStart(now(), toIntervalMinute(1)))
                ),
                60  # increment by 60 seconds (1 minute)
            )
        )
    ) as minute,
    0 as num_trades