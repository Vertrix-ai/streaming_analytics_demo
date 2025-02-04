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

## Installation

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
    ) ENGINE = MergeTree() ORDER BY (time, product_id, sequence);
    ```

7. Run the demo:
   ```bash
   poetry run python streaming_analytics_demo/listen.py --config demo_config.yaml
   ```

8. You should now see data in your clickhouse server
    ```bash
    select * from coinbase_demo.coinbase_ticker;
    ```


## Configuration

The configuration file (`demo_config.yaml`) specifies the sources and sinks for the demo. It configures a coinbase source and a file sink (test.jsonl).






