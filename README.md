# Streaming Analytics Demo

A simple but flexible streaming tool for streaming data for migrating data from a streaming source to a storage system of choice. I built this mainly as a demo tool, and for my own personal amusement, please do not consider it production ready. It does provide a low-lift framework for migrating data in low-stakes situations. Again, this is a demo tool -- If you need a production-ready streaming tool, please use a proven tool like Kafka, Pulsar, Bento, etc.

## Overview

This project demonstrates a modular approach to stream processing with configurable sources and sinks. It uses an extensible architecture that allows for easy addition of new source andsink types through registration. Take a look at streaming_analytics_demo/sinks/file_sink.py for an example of a custom sink.

## Features

- Pluggable source and sink architecture
- JSON schema validation for sink configurations
- Async I/O support
- Built-in sinks:
  - File sink
  - Clickhouse sink
- Built-in sources:
  - Coinbase streaming API

## Missing stuff you'd want for production
 - backpressure handling
 - metrics
 - message specification and validation
 - reconnection
 - liveness checks
 - rate limiting
 - environment variables for configuration

## Configuration

The configuration file (`demo_config.yaml`) specifies the sources and sinks for the demo. It configures a coinbase source and a file sink (test.jsonl).

## Run the demo

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/streaming-analytics-demo.git
   cd streaming-analytics-demo
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Install your sink - I'm using clickhouse here.
    ```bash
    docker pull clickhouse/clickhouse-server:latest
    docker run -d \
        --name clickhouse-server \
        -p 8123:8123 \
        -p 9000:9000
    ```

   When I run this I take another step and map drives onto my local machine to store the data and logs for the clickhouse server. I do this through the following command:
    ```bash
    docker run -d \
        --name clickhouse-server \
        --ulimit nofile=262144:262144 \
        -p 8123:8123 \
        -p 9000:9000 \
        -v $HOME/clickhouse/data:/var/lib/clickhouse \
        -v $HOME/clickhouse/config/clickhouse-server:/etc/clickhouse-server \
        -v $HOME/clickhouse/logs:/var/log/clickhouse-server \
        clickhouse/clickhouse-server:latest
    ```
    Doing it this way requires you to set up the configs, but it has the advantage of persisting across container removals and cleanups.
4. Make sure your clickhouse server is running and accessible.
    ```bash
    docker exec -it clickhouse-server clickhouse-client
    ```
    If you see the clickhouse prompt, then your clickhouse server is running and accessible.

5. Create the database we'll use to store our data.
    ```bash
    CREATE DATABASE IF NOT EXISTS coinbase_demo;
    ```

6. Create the user we'll use to access the database.

    ```sql
    -- Create the user
    CREATE USER coinbase IDENTIFIED BY 'password';

    -- Grant permissions
    GRANT ALL ON coinbase_demo.* TO coinbase;  
    ```
7. Create the table we'll use to store our data.
    ```sql
    CREATE TABLE IF NOT EXISTS coinbase_demo.coinbase_ticker (
        sequence UInt64,
        trade_id UInt64,
        price Float64,
        last_size Float64,
        time DateTime,
        product_id String,
        side String,
        open_24h Float64,
        volume_24h Float64,
        low_24h Float64,
        high_24h Float64,
        volume_30d Float64,
        best_bid Float64,
        best_bid_size Float64,
        best_ask Float64,
        best_ask_size Float64,
    ) ENGINE = MergeTree() ORDER BY (time, product_id, sequence); # Sorting key - maybe not the best - time has a higher cardinality than product_id, bad for generic exclusion algorithm
    ```

8. Run the demo:
   ```bash
   poetry run python streaming_analytics_demo/listen.py --config demo_config.yaml
   ```

9. You should now see data in your clickhouse server
    ```bash
    select * from coinbase_demo.coinbase_ticker;
    ```


## Monitoring

Now that we have some data in our database, let's get some basic observability in place. Unlike batch processing, where there are many tools and libraries to choose from, streaming observability is a bit more ad-hoc. There are few tools that are purpose-built for streaming observability. Since this is a demo, we'll use open source tools to get a basic observability stack. The first, most basic thing we can do is monitor the ingestion rate of our data. Take a look at the `sql/ingestion_monitoring.sql` file for the query we'll use. This query will give us the number of rows ingested per minute, including gaps. If you just ingest for a while, stop it for a few minutes, and rerun, then run this query, you'll see the gaps.

That's a good start, but it's not very useful. We can't really see the big picture. Let's add a few more tools to our stack. We'll start out by installing grafana.

```bash
brew update
brew install grafana
```

Now we'll install the Grafana [Clickhouse plugin](https://grafana.com/docs/grafana/latest/administration/plugin-management/).

Let's also create a user for grafana to access clickhouse. This will be a read-only user.

```sql
CREATE USER IF NOT EXISTS grafana IDENTIFIED WITH sha256_password BY 'password';
GRANT SELECT ON coinbase_demo.* TO grafana;
```

After this we'll need to set up our configuration to allow grafana to access clickhouse. Grafana provides a way to configure plugins in the UI, but in the name of repeatability we'll do it using a [datasource config file](https://grafana.com/docs/grafana/latest/administration/provisioning/#data-sources). One note here: this is a demo, so I left the username and password in observability/.grafana.ini - please don't do this in a production environment.

Now we can place the config file in the grafana provisioning directory and restart grafana.

```bash
cp ~/projects/streaming_analytics_demo/observability/datasource.yaml .
brew services restart grafana
```

Now that we have all of this set up, go to connections->data sources and you should see the clickhouse datasource. Scroll down to the bottom and you'll find a 'Test' button. Click this and you should see a message that says 'Data source is working'.

### Observability Dashboard

Go to the menu and click on 'Dashboards'. Click on 'Create Dashboard' and then 'Add visualization'. Select the clickhouse datasource and 'SQL Editor'. Run the query in the `sql/ingestion_monitoring.sql` file and you'll see a graph of the ingestion rate. Go ahead and click 'Save' and give your dashboard a name.

Now observability isn't just about graphing - we can also use the data to trigger alerts. Let's add an alert to our dashboard. Click on the 'Alerting' tab and then 'New Alert Rule'.

From here we'll add a new query:

```sql
SELECT
    count(sequence)
FROM coinbase_ticker
WHERE time > now() - INTERVAL 1 minute;
```

In the 'options' we'll set this to run every minute.

We'll then add a new 'Threshold' on Input 'A' and set the condition to 'Is Below' 1. As long as you have run your query and see that messages have been receive in the last minute you should see that the alert condition is 'normal'. If you stop ingestion for a minute or two and rerun the query you should see that the alert condition is 'firing'. Now you can go ahead and save the alert and exit. You should see the alert in the 'Alert rules'. There is an option to set up email notifications, but I'll leave that up to you.

Now, go ahead and stop the ingestion and you will see your Alert rule change to 'firing'. You can also go to your dashboard and see that the incoming messages have stopped. You can restart the ingestion and watch the alert return to 'normal'. There is a lot more that can be done here - for example examining sequence number to identify much smaller gaps in the data, but this provides a good starting point.

This also illustrates the importance of monitoring your data. If we hadn't been monitoring, we wouldn't have known that the ingestion had stopped until we got some strange results from our analytics - which may have been too late.

## Improvements

One of the things you'll immediately notice is that in our dashboard we are running a query every minute to refresh the data. Taking a look at the query, on what for clickhouse is quite a small dataset gives the following timing information on my laptop:

```
5304 rows in set. Elapsed: 0.046 sec. Processed 791.55 thousand rows, 8.44 MB (17.23 million rows/s., 183.77 MB/s.)
Peak memory usage: 37.01 MiB.
```

Running that query every minute is a waste of resources. We can do better by using a materialized view. Take a look at sql/ingestion_monitoring_view.sql to see the queries we'll use.

We are first creating a table to store the trades per minute. 

```sql
CREATE TABLE IF NOT EXISTS coinbase_demo.trades_per_minute
(
    minute DateTime,
    num_trades UInt64
) ENGINE = SummingMergeTree()
ORDER BY minute;
```

Notice the use of 'SummingMergeTree()' This is a special engine for summing sequential data. As new data is ingested it is summed up at merge time, maintaining fast inserts, but removing the need to sum all rows each time we query the table. 

We then create a materialized view that updates the trades per minute table.

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS coinbase_demo.trades_per_minute_mv
TO coinbase_demo.trades_per_minute
AS
SELECT 
    tumbleStart(time, toIntervalMinute(1)) as minute,
    countIf(last_size > 0) as num_trades
FROM coinbase_demo.coinbase_ticker
GROUP BY minute;
```

Notice the 'TO' keyword here. This is how we tell the materialized view to update the trades per minute table. The select statement gives the query to source the incoming data, in this case the coinbase ticker table where the raw data is stored.

Frist we'll run the old query against a table where I've had ingestion running for a while - we are processing 916.94 thousand rows - the entire table, which would not scale terribly well.
```
5819 rows in set. Elapsed: 0.025 sec. Processed 916.94 thousand rows, 9.78 MB (36.19 million rows/s., 386.05 MB/s.)
Peak memory usage: 37.02 MiB.
```

Now we'll run a new query that uses the materialized view and produces the same result:

```sql
WITH time_series AS (
    SELECT 
        arrayJoin(
            range(
                toUnixTimestamp(
                    (SELECT min(minute)
                     FROM coinbase_demo.trades_per_minute)
                ),
                toUnixTimestamp(
                    (SELECT tumbleStart(now(), toIntervalMinute(1)))
                ),
                60  # increment by 60 seconds (1 minute)
            )
        ) as minute,
        0 as num_trades
),
-- We need to get the sum of the trades per minute because the 
-- SummingMergeTree delays the summing until merge time. This is 
-- done for insert performance, so the most recent minute may have
-- not been summed yet.
summed_trades AS (
    SELECT 
        minute,
        sum(num_trades) as num_trades
    FROM coinbase_demo.trades_per_minute
    GROUP BY minute
    ORDER BY minute DESC
)
-- Now we join the time series with the summed trades to get the trades
-- per minute.
SELECT 
     fromUnixTimestamp(ts.minute) as minute,
     greatest(ts.num_trades, t.num_trades) as num_trades
FROM time_series ts
LEFT JOIN coinbase_demo.trades_per_minute t ON fromUnixTimestamp(ts.minute) = t.minute
ORDER BY minute DESC;
```

This new query is much more efficient. It processes only the 5834 rows that are currently found in the trades_per_minute table.

```
5834 rows in set. Elapsed: 0.026 sec.
```

While both queries return very quickly on this dataset, the difference will become more pronounced as the dataset grows. In this case Clickhouse's speed was hiding the highly inefficient query from us.

We can now go back to our dashboard and replace the old query with the new one.

# Analytics

Now that we have some data in our database, and have the ability to detect problems with it, let's look at performing some analytics on it. Looking at the tools we have there is an argument that we already have the tools we need - after all, we can run queries in Grafana and create dashboards based on that. The issue is that Grafana is really targetted at observability and time series monitoring. It is designed to be easy for infrastructure teams to work with and does not have the rich user experience, and support for ad hoc analysis that can be found in other tools. So lets integrate a purpose-built BI tool by installing Superset.

## Installation

I'm going to use docker compose to install superset for this demo. This is not a production-grade installation, but it is easy for demo purposes. To start with we'll need to clone the superset repo.

```bash
git clone --depth=1  https://github.com/apache/superset.git
cd superset
```

Before we start the container we'll need to install the dependencies and make some configuration changes. 
 ```bash
touch ./docker/requirements-local.txt
 ```

Edit your new requirements-local.txt file to include the following:

```
clickhouse-connect>=0.6.8
```
Now we can start the container.

```bash
docker compose -f docker-compose-non-dev.yml up
```

This one is going to take a while to start up. It's downloading all the dependencies and building the superset image. Once it has finished you should be able to access the superset UI at http://localhost:8088. Unless you've changed the admin password you can use admin/admin to login. From here click on the '+' on the top right, and select Data -> Connect Database.

If you've succeeded in adding clickhouse then it will be available in the 'supported databases'.

## Analytics

Now that we have the infrastructure in place, let's perform our analytics. We're looking at a trading dataset, so we'll stick with the Genre and build out a dashboard showing the 5 minute Volume Weighted Average Price (VWAP) for the last 24 hours. The first step is to add a Superset dataset with our tick data.

Superset provides multiple ways to do this - we can create a dataset from a table in our database and then build a chart from that using a builder, or we can use the SQL Lab to write a query and then build a chart from that. I'll take the latter approach.

Let's navigate to the SQL Lab and build our query:

```sql
-- construct a series of 5 minute periods for the prior 24 hours
-- which is the period we want to chart
WITH time_series AS (
    SELECT 
        arrayJoin(
            range(
                toUnixTimestamp(
                    (SELECT tumbleStart((now() - INTERVAL 24 HOUR), toIntervalMinute(5)))
                ),
                toUnixTimestamp(
                    (SELECT tumbleStart(now(), toIntervalMinute(5)))
                ),
                300  # increment by 300 seconds (5 minutes)
            )
        ) as interval
),
-- calculate the components of the vwap
vwap AS (
    SELECT 
        tumbleStart(time, toIntervalMinute(5)) as period,
        SUM(price * last_size) as volume_price,
        SUM(last_size) as total_volume
      FROM coinbase_demo.coinbase_ticker
      WHERE 
          period >= now() - INTERVAL 24 HOUR
          AND last_size > 0  -- Filter out zero volume trades
          AND price > 0      -- Filter out invalid prices
      GROUP BY period
)
-- join the vwap calculation to the time series to give the 5 minute vwap for the last 24 hours
SELECT 
    fromUnixTimestamp(interval) as vwap_period,
    IF(v.total_volume > 0, v.volume_price/v.total_volume, 0) as vwap
FROM time_series ts
LEFT JOIN vwap v ON fromUnixTimestamp(ts.interval) = v.period
ORDER BY vwap_period DESC;
```

To build the chart we can just select the chart button below the query, and then fill out the wizard like this:

<insert image>

You can now save the chart, at which point you will be asked which dashboard you'd like to add it to.

<insert image>

Finally we can edit the dashboard by clicking on the '...' and set a refresh interval for the dashboard. That will give us a dashboard updating every 10 seconds. 

The same performance concerns we had with ingestion monitoring apply here, Superset is just rerunning the full query every time. I won't go into how to create the materialized view here - it is the same process we saw before.

# Conclusion

At this point we have data ingestion via a custom python tool, a highly performant data warehouse in clickhouse, data observability via grafana, and analytics via superset.

We've seen how we we can store and query streaming data in clickhouse, how we can use materialized views to offload some of our compute from query time to load time, and how we can present useable tools for analytics and monitoring.

We've delivered value for the end users of the platform - but we're not done. This will hold up well initially, but inevitably on the business side we'll run into questions about what the data means as the number of datasets grows. We'll run into questions about the lineage of our data, and we'll get questions about what assertions we can make about the quality of it.

On the engineering side we also still have work to do - The system appears to work, but as we scale we'll run into problems managing it if we leave it in this state. We've started writing some interesting queries - and the the source of truth for our data models and our transformations is split between the database and our BI tool.We'll run into problems where we break queries, where we have trouble tracking down how datasets are derived, and will very likely cause ourselves production issues as we make changes.

In the next post we'll look at some additional tools we can add to our stack to address these issues.










