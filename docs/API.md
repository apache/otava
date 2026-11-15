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

# Using Otava as a library

Otava can be used without its command line interface and without any of its
importers: build a `Series` from data you already have, analyze it, and read the
change points back.

```python
from otava import AnalysisOptions, Metric, Series

# One measurement per commit. The metric's direction says which way is an
# improvement.
series = Series(
    test_name="send_hello_message",
    branch=None,
    time=list(range(60)),
    metrics={"throughput": Metric(direction=Metric.HIGHER_IS_BETTER, unit="ops/s")},
    data={"throughput": [100.0] * 30 + [80.0] * 30},
    attributes={"commit": [f"sha{i}" for i in range(60)]},
)

analyzed = series.analyze(AnalysisOptions(window_len=20, max_pvalue=0.001))

for change_points_at in analyzed.change_points_by_time:
    for metric, change_point in change_points_at.changes.items():
        print(
            change_points_at.attributes["commit"],
            metric,
            change_point.stats.mean_before(),
            change_point.stats.mean_after(),
            f"{change_point.stats.forward_change_percent():+.1f}%",
        )
```

`analyze()` does not interpret `time`, so a plain index works for data that is
not a time series, but keep it increasing: change points are collected in time
order, and a `ChangePointGroup` that is not later than the previous one raises
`ValueError`. Otava's human-readable log and regression reports do interpret
it, formatting it with `datetime.fromtimestamp`, so those report formats read
it as seconds since the epoch. JSON reports preserve the numeric value.

`attributes` carries one value per data point, and the values at a change point
are returned on its `ChangePointGroup`. That is how you get from a detected
change back to the commit that caused it.

`Series.analyze()` is lazy: the change points are computed the first time any of
the change point properties on `AnalyzedSeries` is read, and cached from then on.
Errors the analysis raises therefore surface at that first read.

## What is public

The names in `otava.__all__`, re-exported from the package root:

| Name | Purpose |
| --- | --- |
| `Series` | Input data: timestamps, metrics, values, per-point attributes |
| `Metric` | Direction (`Metric.HIGHER_IS_BETTER` or `Metric.LOWER_IS_BETTER`), scale and unit of one metric |
| `AnalysisOptions` | `window_len`, `max_pvalue`, `min_magnitude`, `orig_edivisive` |
| `AnalyzedSeries` | Result of `Series.analyze()` |
| `ChangePoint` | One change in one metric; the statistics are on its `stats` |
| `ChangePointGroup` | Changes that share a point in time |
| `ChangePointsByMetric` | Change points keyed by metric |
| `ChangePointsByTime` | Change point groups in time order |

How they fit together:

```text
Series
  .metrics: {metric name: Metric}
  .analyze(AnalysisOptions) -> AnalyzedSeries
                                 .change_points: ChangePointsByMetric
                                 .change_points_by_time: ChangePointsByTime
                                     |
                                     | both hold ChangePointGroup objects
                                     v
                                 ChangePointGroup        one per point in time
                                   .time
                                   .attributes
                                   .changes: {metric name: ChangePoint}
                                                             .stats
```

The supported import surface is the names above when imported from `otava`.
Submodule paths such as `otava.importer`, `otava.config` and `otava.main` are
not part of the public API. Otava does not offer a stable public API yet, so
even the names above can still change in a minor or patch release.

## Options

`AnalysisOptions` holds the settings the `analyze` command exposes as flags,
with the same defaults. The attribute names and the flag names differ; run
`otava analyze --help` for the flags.

| Option | Default | Effect |
| --- | --- | --- |
| `window_len` | 50 | Number of points the algorithm looks at around a candidate; ignored when `orig_edivisive` is set |
| `max_pvalue` | 0.001 | Significance threshold a change point must meet |
| `min_magnitude` | 0.0 | Smallest relative change worth reporting; ignored when `orig_edivisive` is set |
| `orig_edivisive` | False | Use unmodified e-divisive instead of the windowed variant |

See [Change Point Detection](MATH.md) for what these do to the results.
