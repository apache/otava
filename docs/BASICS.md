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
> See [otava.yaml](../examples/csv/otava.yaml) for the full example configuration.

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
> See [otava.yaml](../examples/csv/otava.yaml) for the full
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

The `otava regressions` command can work with feature branches.

First you need to tell Otava how to fetch the data of the tests run against a feature branch.
The `prefix` property of the graphite test definition accepts `%{BRANCH}` variable,
which is substituted at the data import time by the branch name passed to `--branch`
command argument. Alternatively, if the prefix for the main branch of your product is different
from the prefix used for feature branches, you can define an additional `branch_prefix` property.

```yaml
my-product.test-1:
  type: graphite
  tags: [perf-test, daily, my-product, test-1]
  prefix: performance-tests.daily.%{BRANCH}.my-product.test-1
  inherit: common-metrics

my-product.test-2:
  type: graphite
  tags: [perf-test, daily, my-product, test-2]
  prefix: performance-tests.daily.master.my-product.test-2
  branch_prefix: performance-tests.feature.%{BRANCH}.my-product.test-2
  inherit: common-metrics
```

Now you can verify if correct data are imported by running
`otava analyze <test> --branch <branch>`.

The `--branch` argument also works with `otava regressions`. In this case a comparison will be made
between the tail of the specified branch and the tail of the main branch (or a point of the
main branch specified by one of the `--since` selectors).

```
$ otava regressions <test or group> --branch <branch>
$ otava regressions <test or group> --branch <branch> --since <date>
$ otava regressions <test or group> --branch <branch> --since-version <version>
$ otava regressions <test or group> --branch <branch> --since-commit <commit>
```

When comparing two branches, you generally want to compare the tails of both test histories, and
specifically a stable sequence from the end that doesn't contain any changes in itself.
To ignore the older test results, and compare
only the last few points on the branch with the tail of the main branch,
use the `--last <n>` selector. E.g. to check regressions on the last run of the tests
on the feature branch:

```
$ otava regressions <test or group> --branch <branch> --last 1
```

Please beware that performance validation based on a single data point is quite weak
and Otava might miss a regression if the point is not too much different from
the baseline. However, accuracy improves as more data points accumulate, and it is
a normal way of using Otava to just merge a feature and then revert if it is
flagged later.
