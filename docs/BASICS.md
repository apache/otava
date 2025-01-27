# Basics

## Listing Available Tests

```
hunter list-groups
```

Lists all available test groups - high-level categories of tests.

```
hunter list-tests [group name]
```

Lists all tests or the tests within a given group, if the group name is provided.

## Listing Available Metrics for Tests

To list all available metrics defined for the test:

```
hunter list-metrics <test>
```

### Example

> [!TIP]
> See [hunter.yaml](../examples/csv/hunter.yaml) for the full example configuration.

```
$ hunter list-metrics local.sample
metric1
metric2
```

## Finding Change Points

```
hunter analyze <test>...
hunter analyze <group>...
```

This command prints interesting results of all
runs of the test and a list of change-points.
A change-point is a moment when a metric value starts to differ significantly
from the values of the earlier runs and when the difference
is persistent and statistically significant that it is unlikely to happen by chance.
Hunter calculates the probability (P-value) that the change point was caused
by chance - the closer to zero, the more "sure" it is about the regression or
performance improvement. The smaller is the actual magnitude of the change,
the more data points are needed to confirm the change, therefore Hunter may
not notice the regression immediately after the first run that regressed.
However, it will eventually identify the specific commit that caused the regression,
as it analyzes the history of changes rather than just the HEAD of a branch.

The `analyze` command accepts multiple tests or test groups.
The results are simply concatenated.

### Example

> [!TIP]
> See [hunter.yaml](../examples/csv/hunter.yaml) for the full
> example configuration and [local_samples.csv](../examples/csv/data/local_samples.csv)
> for the data.

```
$ hunter analyze local.sample --since=2024-01-01
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
of copy-pasting the definitions  you can use templating capability built-in hunter to define the common bits of configs
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

The `hunter regressions` command can work with feature branches.

First you need to tell Hunter how to fetch the data of the tests run against a feature branch.
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
`hunter analyze <test> --branch <branch>`.

The `--branch` argument also works with `hunter regressions`. In this case a comparison will be made
between the tail of the specified branch and the tail of the main branch (or a point of the
main branch specified by one of the `--since` selectors).

```
$ hunter regressions <test or group> --branch <branch>
$ hunter regressions <test or group> --branch <branch> --since <date>
$ hunter regressions <test or group> --branch <branch> --since-version <version>
$ hunter regressions <test or group> --branch <branch> --since-commit <commit>
```

Sometimes when working on a feature branch, you may run the tests multiple times,
creating more than one data point. To ignore the previous test results, and compare
only the last few points on the branch with the tail of the main branch,
use the `--last <n>` selector. E.g. to check regressions on the last run of the tests
on the feature branch:

```
$ hunter regressions <test or group> --branch <branch> --last 1
```

Please beware that performance validation based on a single data point is quite weak
and Hunter might miss a regression if the point is not too much different from
the baseline. However, accuracy improves as more data points accumulate, and it is
a normal way of using Hunter to just merge a feature and then revert if it is
flagged later.
