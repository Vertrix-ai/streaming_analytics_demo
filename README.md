# Streaming Analytics Demo

A simple but flexible streaming tool for streaming data for migrating data from a streaming source to a storage system of choice. I built this mainly as a demo tool, and for my own personal amusement, please do not consider it production ready. It does provide a low-lift framework for migrating data in low-stakes situations. Again, this is a demo tool -- If you need a production-ready streaming tool, please use a proven tool like Kafka, Pulsar, Bento, etc.

## Overview

This project demonstrates a modular approach to stream processing with configurable output sinks. It uses an extensible architecture that allows for easy addition of new sink types through registration. Take a look at streaming_analytics_demo/sinks/file_sink.py for an example of a custom sink.

## Features

- Pluggable sink architecture
- JSON schema validation for sink configurations
- Async I/O support
- Built-in sinks:
  - File sink
  - Clickhouse sink

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

3. Run the demo:
   ```bash
   poetry run python streaming_analytics_demo/listen.py --config demo_config.yaml
   ```


## Configuration

The configuration file (`demo_config.yaml`) specifies the sources and sinks for the demo. It configures a coinbase source and a file sink (test.jsonl). 




