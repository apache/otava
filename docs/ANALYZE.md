# Finding Change Points

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
not notice the regression after the first run that regressed.

The `analyze` command accepts multiple tests or test groups.
The results are simply concatenated.

#### Example

> [!TIP]
> See [hunter.yaml](../examples/csv/hunter.yaml) for the full example configuration.

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
