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
    docker run -d --name clickhouse-server -p 8123:8123 -p 9000:9000 clickhouse/clickhouse-server:latest
    ```
4. Make sure your clickhouse server is running and accessible.
    ```bash
    docker exec -it clickhouse-server clickhouse-client
    ```
    If you see the clickhouse prompt, then your clickhouse server is running and accessible.
    ```

5. Create the database we'll use to store our data.
    ```bash
    CREATE DATABASE IF NOT EXISTS coinbase_demo;
    ```

6. Create the table we'll use to store our data.
    ```bash
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

7. Run the demo:
   ```bash
   poetry run python streaming_analytics_demo/listen.py --config demo_config.yaml
   ```

8. You should now see data in your clickhouse server
    ```bash
    select * from coinbase_demo.coinbase_ticker;
    ```


## Monitoring

Now that we have some data in our databawse, let's get some basic observability in place. Unlike batch processing, where there are many tools and libraries to choose from, streaming observability is a bit more ad-hoc. There are few tools that are purpose-built for streaming observability, and many of them are quite expensive. Since this is a demo, we'll use a combination of open source tools to get a basic observability stack. The first, most basic thing we can do is monitor the ingestion rate of our data. Take a look at the `sql/ingestion_monitoring.sql` file for the query we'll use. This query will give us the number of rows ingested per minute, including gaps. If you just ingest for a while, stop it for a few minutes, and rerun, then run this query, you'll see the gaps.

That's a good start, but it's not very useful. We can't really see the big picture. Let's add a few more tools to our stack. We'll start out by installing grafana.

```bash
brew update
brew install grafana
```

Now we'll install the Grafana [Clickhouse plugin](https://grafana.com/docs/grafana/latest/administration/plugin-management/).

Let's also create a user for grafana to access clickhouse. This will be a read-only user.

```bash
CREATE USER IF NOT EXISTS grafana IDENTIFIED WITH sha256_password BY 'password';
GRANT SELECT ON coinbase_demo.* TO grafana_user;
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








