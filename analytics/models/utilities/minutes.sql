{{ config(
    materialized='ephemeral',
    order_by='minute'
) }}

-- Get all trades
WITH trades AS (
    SELECT * from {{ ref('stg_coinbase__trades') }}
)
SELECT
    toDateTime( -- Convert the unix timestamp to a datetime
        arrayJoin( -- Get all minutes in the range
            range(
                toUnixTimestamp( -- Get the start of the first minute
                    (SELECT tumbleStart(min(trade_time), toIntervalMinute(1))
                        FROM trades)
                ),
                toUnixTimestamp( -- Get the start of the last minute
                    (SELECT tumbleStart(now(), toIntervalMinute(1)))
                ),
                60  # increment by 60 seconds (1 minute)
            )
        )
    ) as minute,
    0 as num_trades