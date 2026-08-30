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

# Getting Started

## Installation

Otava requires Python 3.10 or later.

```bash
pip install apache-otava
```

This installs the Otava library and CLI with CSV, JSON, and Graphite
support. Install the extra for any additional service you use, for example:

```bash
pip install 'apache-otava[postgres]'
pip install 'apache-otava[bigquery,slack]'
```

See [Installation](INSTALL.md) for the complete list of extras.

or

```bash
docker pull apache/otava
```

The Docker image includes all optional integrations.


## Setup

By default, Otava reads configuration from `~/.otava/otava.yaml`. Create that
file and add the data sources and tests you want to analyze.

To run the bundled CSV example from a source checkout, use its local
configuration while running the commands in this guide:

```bash
export OTAVA_CONFIG=examples/csv/config/otava-local.yaml
```

> [!TIP]
> See docs on specific data sources to learn more about their configuration - [CSV](CSV.md), [Graphite](GRAPHITE.md),
[PostgreSQL](POSTGRESQL.md), or [BigQuery](BIG_QUERY.md).

Alternatively, it is possible to leave the config file as is, and provide credentials in the environment
by setting appropriate environment variables.
Environment variables are interpolated before interpreting the configuration file.

## Defining tests

All test configurations are defined in the main configuration file.
Otava supports reading data from and publishing results to a CSV file, [Graphite](https://graphiteapp.org/),
[PostgreSQL](https://www.postgresql.org/), and [BigQuery](https://cloud.google.com/bigquery).

Tests are defined in the `tests` section. For example, the following definition will import results of the test from a CSV file:

```yaml
tests:
  local.sample:
    type: csv
    file: tests/resources/sample.csv
    time_column: time
    metrics: [metric1, metric2]
    attributes: [commit]
    csv_options:
      delimiter: ","
      quote_char: "'"
```

The `time_column` property points to the name of the column storing the timestamp
of each test-run. The data points will be ordered by that column.

The `metrics` property selects the columns that hold the values to be analyzed. These values must
be numbers convertible to floats. The `metrics` property can be not only a simple list of column
names, but it can also be a dictionary configuring other properties of each metric,
the column name or direction:

```yaml
metrics:
  resp_time_p99:
    direction: -1
    column: p99
```

Direction can be 1 or -1. If direction is set to 1, this means that the higher the metric, the
better the performance is. If it is set to -1, higher values mean worse performance.

The `attributes` property describes any other columns that should be attached to the final
report. Special attribute `version` and `commit` can be used to query for a given time-range.

> [!TIP]
> To learn how to avoid repeating the same configuration in multiple tests,
> see [Avoiding test definition duplication](BASICS.md#avoiding-test-definition-duplication).

## Listing Available Tests

```
otava list-groups
otava list-tests [group name]
```

## Listing Available Metrics for Tests

To list all available metrics defined for the test:
```
otava list-metrics <test>
```

## Finding Change Points

> [!TIP]
> For more details, see [Finding Change Points](BASICS.md#finding-change-points) and
> [Validating Performance of a Feature Branch](BASICS.md#validating-performance-of-a-feature-branch).

```
otava analyze <test>...
otava analyze <group>...
```

This command prints interesting results of all runs of the test and a list of change-points.

A change-point is a moment when a metric value starts to differ significantly from the values of the earlier runs and
when the difference is statistically significant.

Otava calculates the probability (P-value) that the change point was not caused by chance - the closer to zero, the more
certain it is about the regression or performance improvement. The smaller the magnitude of the change, the
more data points are needed to confirm the change, therefore Otava may not notice the regression immediately after the first run
that regressed.

The `analyze` command accepts multiple tests or test groups.
The results are simply concatenated.

## Example

```console
$ otava analyze local.sample --since=2026-01-01T00:00:00Z
INFO: Computing change points for test local.sample...
time                       commit      metric1    metric2
-------------------------  --------  ---------  ---------
2026-01-01 02:00:00 +0000  aaa0         154023      10.43
2026-01-02 02:00:00 +0000  aaa1         138455      10.23
2026-01-03 02:00:00 +0000  aaa2         143112      10.29
2026-01-04 02:00:00 +0000  aaa3         149190      10.91
2026-01-05 02:00:00 +0000  aaa4         132098      10.34
2026-01-06 02:00:00 +0000  aaa5         151344      10.69
                                                ·········
                                                   -12.9%
                                                ·········
2026-01-07 02:00:00 +0000  aaa6         155145       9.23
2026-01-08 02:00:00 +0000  aaa7         148889       9.11
2026-01-09 02:00:00 +0000  aaa8         149466       9.13
2026-01-10 02:00:00 +0000  aaa9         148209       9.03
```
