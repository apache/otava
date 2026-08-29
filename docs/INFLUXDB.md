<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 -->

# Importing results from InfluxDB 3

Otava imports query results from InfluxDB 3 Core or Enterprise through the
[`influxdb3-python`](https://docs.influxdata.com/influxdb3/core/reference/client-libraries/v3/python/)
client. SQL is the default query language; set `query_language: influxql` for
InfluxQL queries.

## Installation

```bash
pip install 'apache-otava[influxdb]'
```

## Connection

```yaml
influxdb:
  host: http://localhost:8181
  database: performance
  token: ${INFLUXDB_TOKEN}
```

The same settings are available through `INFLUXDB_HOST`, `INFLUXDB_DATABASE`,
and `INFLUXDB_TOKEN`, or the `--influxdb-host`, `--influxdb-database`, and
`--influxdb-token` command-line options. Command-line values take precedence
over environment variables, which take precedence over YAML.

## Reproducible example

The bundled example starts InfluxDB 3 Core with authenticated, in-memory
storage, seeds deterministic latency data, and runs Otava against it:

```bash
docker build -t apache/otava:latest .
docker compose -f examples/influxdb/docker-compose.yaml run --rm otava \
  analyze api_latency_sql --branch main --since 2025-01-01
docker compose -f examples/influxdb/docker-compose.yaml down
```

Run `api_latency_influxql` instead to query the same data with InfluxQL.

The admin token committed under `examples/influxdb/` is a fixed test
credential, and the server discards its in-memory data when stopped. Both are
for this local demonstration only. Use a securely generated token and durable
object storage for production deployments.

## Test configuration

```yaml
tests:
  api_latency_sql:
    type: influxdb
    query_language: sql
    query: |
      SELECT time, branch, p95_ms, commit
      FROM api_latency
      WHERE branch = %{BRANCH}
      ORDER BY time
    time_column: time
    attributes: [branch, commit]
    metrics:
      p95:
        column: p95_ms
        direction: -1
        scale: 1

  legacy_api_latency:
    type: influxdb
    query_language: influxql
    query: SELECT time, branch, p95_ms FROM api_latency WHERE branch = %{BRANCH}
    attributes: [branch]
    metrics: [p95_ms]
```

Metric definitions use `column`, `direction`, and `scale` as with the other
SQL-backed importers. `%{BRANCH}` is replaced with an escaped string literal
when `--branch` is supplied.

Run the analysis with:

```bash
otava analyze api_latency_sql --branch main --last 100
```

InfluxDB is import-only in this release; Otava does not write change points
back to InfluxDB.
