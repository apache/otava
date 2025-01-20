# Validating Performance of a Feature Branch

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
the baseline. 