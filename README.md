# Streaming Analytics Demo

## Ingestion tool
A simple but flexible streaming tool for streaming data for migrating data from a streaming source to a storage system of choice. I built this mainly as a demo tool, and for my own personal amusement, please do not consider it production ready. It does provide a low-lift framework for migrating data in low-stakes situations. Again, this is a demo tool -- If you need a production-ready streaming tool, please use a proven tool like Kafka, Pulsar, Bento, etc.

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

3. Install your sink - I'm using clickhouse here. I'm using docker volumes here to ensure that the data is persisted across container removals and cleanups. Using bind mounts doesn't work because the permissions for newly created tables are set so that we can't drop tables.
    ```bash
    docker pull clickhouse/clickhouse-server:latest

    docker volume create clickhouse-data
    docker volume create clickhouse-logs
    docker volume create clickhouse-config

    docker run -d \                      
        --name clickhouse-server \
        --ulimit nofile=262144:262144 \
        -p 8123:8123 \
        -p 9000:9000 \
        -v clickhouse-data:/var/lib/clickhouse \
        -v clickhouse-config:/etc/clickhouse-server \
        -v clickhouse-logs:/var/log/clickhouse-server clickhouse/clickhouse-server:latest
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
        -e CLICKHOUSE_USER=default \
        -e CLICKHOUSE_PASSWORD=yourpassword \
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

# The rest of the README describes the configuration of 3rd party tools to create a simple but effective data platform for streaming data.

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

# Maintainability

Install DBT - I considered using both DBT and sqlmesh for this demo, but decided to go with DBT for the following reasons:

DBT is more mature
It has a larger installed base
SQL Mesh has a couple of advantages over DBT - more efficient incremental processing and column-level lineage, but since I'm using clickhouse for materialization and will later integrate OpenMetadata for lineage those advantages are less important for this project. SQLMesh does have the advantage of virtual environments, but I think that is outweighed by DBTs integrations for my purposes.

# Installing DBT

We'll start with a manual installation of DBT core. Since this is for local development we'll add it using poetry with

```bash
poetry add dbt-core@~1.8.0
```

I'm restricting the version to ~1.8.0 for compatibility with dbt-clickhouse, which is slightly behind the latest version of dbt-core.

Now I'll add the clickhouse adapter with 

```bash
poetry add dbt-clickhouse
```

Finally I'll install both dependencies and check to make sure it's working:

```bash
poetry install
dbt --version
```

## Set Up a Project

```bash
dbt init
```

When asked which database you'd like to use, select clickhouse.

I've done one thing a bit unusual here - I've made the dbt project a subdirectory of a larger project. Since I did that I couldn't use the default project name, so I'm going to change in in the analytics/dbt_project.yml file.

```yaml
# Name your project! Project names should contain only lowercase characters
# and underscores. A good package name should reflect your organization's
# name or the intended use of these models
name: 'streaming_analytics_demo'
version: '1.0.0'

# This setting configures which "profile" dbt uses for this project.
profile: 'streaming_analytics_demo'
```

## Connect to clickhouse

With that done we have the basic project set up. Now we need to connect to clickhouse. We'll do that by setting up a profile in ~/.dbt/profiles.yml. This will hold our connection details:

```yaml
streaming_analytics_demo:
  target: dev
  outputs:
    dev:
      type: clickhouse
      schema: coinbase_demo
      host: localhost
      port: 8123
      user: coinbase
      password: password
      secure: False
```

Now test the connection by running 

```bash
cd analytics
dbt debug
```

You should see something like the following:

```bash
21:30:25    tcp_keepalive: False
21:30:25  Registered adapter: clickhouse=1.8.9
21:30:25    Connection test: [OK connection ok]

21:30:25  All checks passed!
```

If you see an error about failing to drop tables, then you may need to adjust the permissions on the clickhouse data directory.

Before we start creating our own models I'll drop the 'example' model that dbt creates by default

```bash
rm -rf models/example
```


## Set up our models

Now that we're connected to clickhouse I'll set up our models. This is where we start creating a maintainable structure. I'm going to be basing the structure of this project on the ['Best Practices' guide from dbt](https://docs.getdbt.com/best-practices). The first structure to add is staging models for the coinbase source. In staging we're going to limit the transformations to simple lossless transformations like renamings, converting units, etc. 

```
mkdir -p models/coinbase
```

In this directory we'll create a file called _coinbase__sources.sql. This file will give a reference to the data we are using as the basis for our transformations.

```yaml
version: 2

sources:
  - name: stg_coinbase__sources
    schema: coinbase_demo
    description: "Raw coinbase data"
    tables:
      - name: coinbase_ticker
        description: "Messages from the coinbase 'ticker' channel"
        columns:
          - name: sequence
            description: "The sequence number of the message. Missing sequence numbers 
            indicate missed messages. We expect gaps in this table because ticks do not represent the full feed."
            data_tests:
              - unique
              - not_null
          - name: trade_id
            description: "The unique ID of the trade. We expect no gaps in this dataset because we should have every trade."
            data_tests:
              - unique
              - not_null
          - name: price
            descrption: "the price in the base currency at which the trade was executed."
            data_tests:
              - not_null
          - name: last_size
            description: "The size of the last trade."
            data_tests:
              - not_null
          - name: time
            description: "The ISO 8601 timestamp of the trade."
            data_tests:
              - not_null
          - name: product_id
            description: "The product ID (e.g. 'BTC-USD') of the product for which the trade was executed."
          - name: side
            description: "The side of the trade (buy or sell)"
            data_tests:
              - accepted_values:
                  values: ['buy', 'sell']
          - name: open_24h
            description: "The opening price 24 hours ago."
            data_tests:
              - not_null
          - name: volume_24h
            description: "The volume of trading activity in the last 24 hours."
            data_tests:
              - not_null
          - name: low_24h
            description: "The lowest price in the last 24 hours."
            data_tests:
              - not_null
          - name: high_24h
            description: "The highest price in the last 24 hours."
            data_tests:
              - not_null
          - name: volume_30d
            description: "The volume of trading activity in the last 30 days."
            data_tests:
              - not_null
          - name: best_bid
            description: "The highest bid price."
            data_tests:
              - not_null
          - name: best_ask
            description: "The lowest ask price."
            data_tests:
              - not_null
          - name: best_bid_size
            description: "The size of the best bid."
            data_tests:
              - not_null
          - name: best_ask_size
            description: "The size of the best ask."
            data_tests:
              - not_null
```

There are a couple of things worth mentioning here:
- For most data stores dbt uses a combination of 'database' and 'schema' to identify the source. Clickhouse is unusual in that it only requires a 'schema' to identify the source where the 'schema' in the sources yaml is the name of the clickhouse database. We've also defined some basic tests for the data in the source table. 

With the source table fully defined I'm going to create the staging model. In this case there is going to be a single model where I'm really just renaming a bit.

```bash
touch staging/coinbase/_coinbase__trades.sql
```

The contents of that file are:

```sql
with 
source as (
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
```

With that done we can run

```bash
dbt run
```

and we'll see that we have a new view in our clickhouse database reflecting the coinbase_tickers table, with fields renamed as we specified in our model.

This will create a new directory called models/coinbase/staging and put the coinbase_tickers table in it.

We've also defined tests for the source data. the tests we are currently using are all dbt built in tests. Executing

```bash
dbt test
```

will run the tests. Right now everything should pass, though if you change one of the values for 'side' you'll be able to see the tests fail. I make a habit of running dbt test after every change I make to the models. This gives a strong signal that my changes have not broken anything in the data.

Now that we have a staging model to represent the data as we receive it, we can start transforming it into the shape we'll need for our analytics. In the last post we saw that for both the monitoring use case - tracking trades in the last minute - and the analytics use case - tracking the 5 minute VWAP - we'll look to roll up the trades into a time-based aggregation. This is the first place we'll need to make a decision about the best practices for structure - do we create an aggregate in staging which we share, or do we create one model for data ops, and another for trading? I'm going to take an educated guess that it will be easier to maintain if we create one model in sharing and build business focused intermediate models off of that common core.

I'm also going to decide that I'll create the new model in the same sql file. 


add the model to the dbt_project.yml file
```yaml
models:
  analytics:
    # This is the default materialization for all models in the staging directory
    staging:
      +materialized: view
    intermediate:
      +materialized: table
```

Since we are also creating a new model I will create tests for that as well. DBT supports both a concept of data tests and unit tests. You saw data tests above. A key difference is that data tests are run after the model is created, and are designed to test the data in the model. Unit tests are designed to test the logic of the model on static data. 

Unit tests therefore give us a way to catch regressions before we try it on real data. 



# Conclusion

At this point we have data ingestion via a custom python tool, a highly performant data warehouse in clickhouse, data observability via grafana, and analytics via superset.

We've seen how we we can store and query streaming data in clickhouse, how we can use materialized views to offload some of our compute from query time to load time, and how we can present useable tools for analytics and monitoring.

We've delivered value for the end users of the platform - but we're not done. This will hold up well initially, but inevitably on the business side we'll run into questions about what the data means as the number of datasets grows. We'll run into questions about the lineage of our data, and we'll get questions about what assertions we can make about the quality of it.

On the engineering side we also still have work to do - The system appears to work, but as we scale we'll run into problems managing it if we leave it in this state. We've started writing some interesting queries - and the the source of truth for our data models and our transformations is split between the database and our BI tool.We'll run into problems where we break queries, where we have trouble tracking down how datasets are derived, and will very likely cause ourselves production issues as we make changes.

In the next post we'll look at some additional tools we can add to our stack to address these issues.










