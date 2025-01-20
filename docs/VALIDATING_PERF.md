# Validating Performance against Baseline

Often we want to know if the most recent product version  
performs at least as well as one of the previous releases. It is hard to tell that by looking
at the individual change points. Therefore, Hunter provides a separate command for comparing
the current performance with the baseline performance level denoted by `--since-XXX` selector:

```
$ hunter regressions <test or group> 
$ hunter regressions <test or group> --since <date>
$ hunter regressions <test or group> --since-version <version>
$ hunter regressions <test or group> --since-commit <commit>
```

If there are no regressions found in any of the tests, Hunter prints `No regressions found` message. Otherwise, it 
gives a list of tests with metrics and magnitude of regressions.

In this test, Hunter compares performance level around the baseline ("since") point with the performance level at the 
end of the time series. If the baseline point is not specified, the beginning of the time series is assumed. The 
"performance level at the point" is computed from all the data points between two nearest change points. Then, two such
selected fragments are compared using Student's T-test for statistical differences.

### Examples

> [!TIP]
> See [hunter.yaml](../examples/csv/hunter.yaml) for the full example configuration.

```
$ hunter regressions local.sample --since=2024-01-01
INFO: Computing change points for test local.sample...
local.sample:
    metric2         :     10.5 -->     9.12 ( -12.9%)
Regressions in 1 test found

$ hunter regressions local.sample --since '2024-01-07 02:00:00'
INFO: Computing change points for test local.sample...
local.sample: OK
No regressions found!

$ hunter regressions local.sample --since-commit 'aaa5'
local.sample:
    metric2         :     10.5 -->     9.38 ( -10.6%)
Regressions in 1 test found
```

