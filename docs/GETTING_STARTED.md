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

Otava requires Python 3.8.  If you don't have python 3.8,
use pyenv to install it.

Use pipx to install otava:

```
pipx install git+ssh://git@github.com/apache/otava
```

## Setup

Copy the main configuration file `resources/otava.yaml` to `~/.otava/otava.yaml` and adjust data source configuration.

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

```
$ otava analyze local.sample
INFO: Computing change points for test sample.csv...
sample:
time                         metric1    metric2
-------------------------  ---------  ---------
2021-01-01 02:00:00 +0000     154023      10.43
2021-01-02 02:00:00 +0000     138455      10.23
2021-01-03 02:00:00 +0000     143112      10.29
2021-01-04 02:00:00 +0000     149190      10.91
2021-01-05 02:00:00 +0000     132098      10.34
2021-01-06 02:00:00 +0000     151344      10.69
                                      ·········
                                         -12.9%
                                      ·········
2021-01-07 02:00:00 +0000     155145       9.23
2021-01-08 02:00:00 +0000     148889       9.11
2021-01-09 02:00:00 +0000     149466       9.13
2021-01-10 02:00:00 +0000     148209       9.03
```
