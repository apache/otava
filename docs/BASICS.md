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

# Basics

## Listing Available Tests

```
otava list-groups
```

Lists all available test groups - high-level categories of tests.

```
otava list-tests [group name]
```

Lists all tests or the tests within a given group, if the group name is provided.

## Listing Available Metrics for Tests

To list all available metrics defined for the test:

```
otava list-metrics <test>
```

### Example

> [!TIP]
> See [otava.yaml](../examples/csv/config/otava.yaml) for the full example configuration.

```
$ otava list-metrics local.sample
metric1
metric2
```

## Finding Change Points

```
otava analyze <test>...
otava analyze <group>...
```

This command prints interesting results of all
runs of the test and a list of change-points.
A change-point is a moment when a metric value starts to differ significantly
from the values of the earlier runs and when the difference
is persistent and statistically significant that it is unlikely to happen by chance.
Otava calculates the probability (P-value) that the change point was caused
by chance - the closer to zero, the more "sure" it is about the regression or
performance improvement. The smaller is the actual magnitude of the change,
the more data points are needed to confirm the change, therefore Otava may
not notice the regression immediately after the first run that regressed.
However, it will eventually identify the specific commit that caused the regression,
as it analyzes the history of changes rather than just the HEAD of a branch.

The `analyze` command accepts multiple tests or test groups.
The results are simply concatenated.

### Example

> [!TIP]
> See [otava.yaml](../examples/csv/config/otava.yaml) for the full
> example configuration and [local_samples.csv](../examples/csv/data/local_samples.csv)
> for the data.

```
$ otava analyze local.sample --since=2024-01-01
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

## Avoiding test definition duplication

You may find that your test definitions are very similar to each other,  e.g. they all have the same metrics. Instead
of copy-pasting the definitions  you can use templating capability built-in otava to define the common bits of configs
separately.

First, extract the common pieces to the `templates` section:
```yaml
templates:
  common-metrics:
    throughput:
      suffix: client.throughput
    response-time:
      suffix: client.p50
      direction: -1    # lower is better
    cpu-load:
      suffix: server.cpu
      direction: -1    # lower is better
```

Next you can recall a template in the `inherit` property of the test:

```yaml
my-product.test-1:
  type: graphite
  tags: [perf-test, daily, my-product, test-1]
  prefix: performance-tests.daily.my-product.test-1
  inherit: common-metrics
my-product.test-2:
  type: graphite
  tags: [perf-test, daily, my-product, test-2]
  prefix: performance-tests.daily.my-product.test-2
  inherit: common-metrics
```

You can inherit more than one template.

## Validating Performance of a Feature Branch

When developing a feature, you may want to analyze performance test results from a specific branch
to detect any regressions introduced by your changes. The `--branch` option allows you to run
change-point analysis on branch-specific data.

### Configuration

To support branch-based analysis, use the `%{BRANCH}` placeholder in your test configuration.
This placeholder will be replaced with the branch name specified via `--branch`:

```yaml
tests:
  my-product.test:
    type: graphite
    prefix: performance-tests.%{BRANCH}.my-product
    tags: [perf-test, my-product]
    metrics:
      throughput:
        suffix: client.throughput
        direction: 1
      response_time:
        suffix: client.p50
        direction: -1
```

For PostgreSQL or BigQuery tests, use `%{BRANCH}` in your SQL query:

```yaml
tests:
  my-product.db-test:
    type: postgres
    time_column: commit_ts
    attributes: [experiment_id, commit]
    query: |
      SELECT commit, commit_ts, throughput, response_time
      FROM results
      WHERE branch = %{BRANCH}
      ORDER BY commit_ts ASC
    metrics:
      throughput:
        direction: 1
      response_time:
        direction: -1
```

For CSV data sources, the branching is done by looking at the `branch` column in the CSV file and filtering rows based on the specified branch value.

### Usage

Run the analysis with the `--branch` option:

```
otava analyze my-product.test --branch feature-xyz
```

This will:
1. Fetch data from the branch-specific location.
2. Run change-point detection on the branch's performance data

### Example

```
$ otava analyze my-product.test --branch feature-new-cache --since=-30d
INFO: Computing change points for test my-product.test...
my-product.test:
time                         throughput    response_time
-------------------------  ------------  ---------------
2024-01-15 10:00:00 +0000        125000            45.2
2024-01-16 10:00:00 +0000        124500            44.8
2024-01-17 10:00:00 +0000        126200            45.1
                               ········
                                 +15.2%
                               ········
2024-01-18 10:00:00 +0000        145000            38.5
2024-01-19 10:00:00 +0000        144200            39.1
2024-01-20 10:00:00 +0000        146100            38.2
```

The `--branch` option can also be set via the `BRANCH` environment variable:

```
BRANCH=feature-xyz otava analyze my-product.test
```