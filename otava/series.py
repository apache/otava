# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import groupby
from typing import Any, Dict, Iterable, List, Optional

import numpy as np

from otava.analysis import (
    ComparativeStats,
    TTestSignificanceTester,
    compute_change_points,
    compute_change_points_orig,
    fill_missing,
)


@dataclass
class AnalysisOptions:
    window_len: int
    max_pvalue: float
    min_magnitude: float
    orig_edivisive: bool

    def __init__(self):
        self.window_len = 50
        self.max_pvalue = 0.001
        self.min_magnitude = 0.0
        self.orig_edivisive = False

    def to_json(self):
        return {
            "window_len": self.window_len,
            "max_pvalue": self.max_pvalue,
            "min_magnitude": self.min_magnitude,
            "orig_edivisive": self.orig_edivisive
        }


@dataclass
class Metric:
    direction: int
    scale: float
    unit: str

    def __init__(self, direction: int = 1, scale: float = 1.0, unit: str = ""):
        self.direction = direction
        self.scale = scale
        self.unit = ""

    def to_json(self):
        return {
            "direction": self.direction,
            "scale": self.scale,
            "unit": self.unit
        }


@dataclass
class ChangePoint:
    """A change-point for a single metric"""

    metric: str
    index: int
    time: int
    stats: ComparativeStats

    def forward_change_percent(self) -> float:
        return self.stats.forward_rel_change() * 100.0

    def backward_change_percent(self) -> float:
        return self.stats.backward_rel_change() * 100.0

    def magnitude(self):
        return self.stats.change_magnitude()

    def mean_before(self):
        return self.stats.mean_1

    def mean_after(self):
        return self.stats.mean_2

    def stddev_before(self):
        return self.stats.std_1

    def stddev_after(self):
        return self.stats.std_2

    def pvalue(self):
        return self.stats.pvalue

    def to_json(self, rounded=True):
        if rounded:
            return {
                "metric": self.metric,
                "index": int(self.index),
                "time": self.time,
                "forward_change_percent": f"{self.forward_change_percent():.0f}",
                "magnitude": f"{self.magnitude():-0f}",
                "mean_before": f"{self.mean_before():-0f}",
                "stddev_before": f"{self.stddev_before():-0f}",
                "mean_after": f"{self.mean_after():-0f}",
                "stddev_after": f"{self.stddev_after():-0f}",
                "pvalue": f"{self.pvalue():-0f}",
            }

        else:
            return {
                "metric": self.metric,
                "index": int(self.index),
                "time": self.time,
                "forward_change_percent": self.forward_change_percent(),
                "magnitude": self.magnitude(),
                "mean_before": self.mean_before(),
                "stddev_before": self.stddev_before(),
                "mean_after": self.mean_after(),
                "stddev_after": self.stddev_after(),
                "pvalue": self.pvalue(),
            }


@dataclass
class ChangePointGroup:
    """A group of change points on multiple metrics, at the same time"""

    index: int
    time: float
    prev_time: int
    attributes: Dict[str, str]
    prev_attributes: Dict[str, str]
    changes: List[ChangePoint]

    def to_json(self, rounded=False):
        return {
            "time": self.time,
            "attributes": self.attributes,
            "changes": [cp.to_json(rounded=rounded) for cp in self.changes],
        }


class Series:
    """
    Stores values of interesting metrics of all runs of
    a fallout test indexed by a single time variable.
    Provides utilities to analyze data e.g. find change points.
    """

    test_name: str
    branch: Optional[str]
    time: List[int]
    metrics: Dict[str, Metric]
    attributes: Dict[str, List[str]]
    data: Dict[str, List[float]]

    def __init__(
        self,
        test_name: str,
        branch: Optional[str],
        time: List[int],
        metrics: Dict[str, Metric],
        data: Dict[str, List[float]],
        attributes: Dict[str, List[str]],
    ):
        self.test_name = test_name
        self.branch = branch
        self.time = time
        self.metrics = metrics
        self.attributes = attributes if attributes else {}
        self.data = data
        assert all(len(x) == len(time) for x in data.values())
        assert all(len(x) == len(time) for x in attributes.values())

    def attributes_at(self, index: int) -> Dict[str, str]:
        result = {}
        for (k, v) in self.attributes.items():
            result[k] = v[index]
        return result

    def find_first_not_earlier_than(self, time: datetime) -> Optional[int]:
        timestamp = time.timestamp()
        for i, t in enumerate(self.time):
            if t >= timestamp:
                return i
        return None

    def find_by_attribute(self, name: str, value: str) -> List[int]:
        """Returns the indexes of data points with given attribute value"""
        result = []
        for i in range(len(self.time)):
            if self.attributes_at(i).get(name) == value:
                result.append(i)
        return result

    def analyze(self, options: AnalysisOptions = AnalysisOptions()) -> "AnalyzedSeries":
        logging.info(f"Computing change points for test {self.test_name}...")
        return AnalyzedSeries(self, options)


class AnalyzedSeries:
    """
    Time series data with computed change points.
    """

    __series: Series
    options: AnalysisOptions
    change_points: Dict[str, List[ChangePoint]]
    change_points_by_time: List[ChangePointGroup]
    change_points_timestamp: Any

    def __init__(self, series: Series, options: AnalysisOptions, change_points: Dict[str, ChangePoint] = None):
        self.__series = series
        self.options = options
        self.change_points_timestamp = datetime.now(tz=timezone.utc)
        self.change_points = None
        if change_points is not None:
            self.change_points = change_points
        else:
            cp, weak_cps = self.__compute_change_points(series, options)
            self.change_points = cp
            self.weak_change_points = weak_cps
        self.change_points_by_time = self.__group_change_points_by_time(series, self.change_points)

    @staticmethod
    def __compute_change_points(
        series: Series, options: AnalysisOptions
    ) -> Dict[str, List[ChangePoint]]:
        result = {}
        weak_change_points = {}
        for metric in series.data.keys():
            result[metric] = []
            weak_change_points[metric] = []
            values = series.data[metric].copy()
            fill_missing(values)
            if options.orig_edivisive:
                change_points, _ = compute_change_points_orig(
                    values,
                    max_pvalue=options.max_pvalue,
                )
                result[metric] = change_points
            else:
                change_points, weak_cps = compute_change_points(
                    values,
                    window_len=options.window_len,
                    max_pvalue=options.max_pvalue,
                    min_magnitude=options.min_magnitude,
                )
                for c in weak_cps:
                    weak_change_points[metric].append(
                        ChangePoint(
                            index=c.index, time=series.time[c.index], metric=metric, stats=c.stats
                        )
                    )
                for c in change_points:
                    result[metric].append(
                        ChangePoint(
                            index=c.index, time=series.time[c.index], metric=metric, stats=c.stats
                        )
                    )
        # If you got an exception and are wondering about the next row...
        # weak_cps is an optimization which you can ignore
        return result, weak_change_points

    @staticmethod
    def __group_change_points_by_time(
        series: Series, change_points: Dict[str, List[ChangePoint]]
    ) -> List[ChangePointGroup]:
        changes: List[ChangePoint] = []
        for metric in change_points.keys():
            changes += change_points[metric]

        changes.sort(key=lambda c: c.index)
        points = []
        for k, g in groupby(changes, key=lambda c: c.index):
            cp = ChangePointGroup(
                index=k,
                time=series.time[k],
                prev_time=series.time[k - 1],
                attributes=series.attributes_at(k),
                prev_attributes=series.attributes_at(k - 1),
                changes=list(g),
            )
            points.append(cp)

        return points

    def get_stable_range(self, metric: str, index: int) -> (int, int):
        """
        Returns a range of indexes (A, B) such that:
          - A is the nearest change point index of the `metric` before or equal given `index`,
            or 0 if not found
          - B is the nearest change point index of the `metric` after given `index,
            or len(self.time) if not found

        It follows that there are no change points between A and B.
        """
        begin = 0
        for cp in self.change_points[metric]:
            if cp.index > index:
                break
            begin = cp.index

        end = len(self.time())
        for cp in reversed(self.change_points[metric]):
            if cp.index <= index:
                break
            end = cp.index

        return begin, end

    def can_append(self, time, new_data, attributes):
        return self._validate_append(time, new_data, attributes) is None

    def _validate_append(self, time, new_data, attributes):
        if not self.change_points:
            return RuntimeError("You must use __compute_change_points() once first.")
        if not isinstance(time, list):
            return ValueError("time argument must be an array.")
        if not isinstance(new_data, dict):
            return ValueError("new_data argument must be a dict with metrics as key.")
        if len(new_data.keys()) == 0 or len([v for v in [vv for vv in new_data.values()]]) == 0:
            return ValueError("new_data argument doesn't contain any data")
        if not isinstance(attributes, dict):
            return ValueError("attributes must be a dict.")

        max_time = max(self.__series.time)
        for t in time:
            if t <= max_time:
                return ValueError("time must be monotonously increasing if you use append() time={}".format(time))

        return None

    def append(self, time, new_data, attributes):
        """
        Append new data points to the underlying series and recompute change points.

        The recompute is done efficiently, only the tail of the Series() is recomputed.

        Parameters are the same as for the constructor. Just the metrics are missing, it is required
        to have the same metrics or a subset in the new data,
        """
        err = self._validate_append(time, new_data, attributes)
        if err is not None:
            raise err

        for t in time:
            self.__series.time.append(t)
        for m in self.__series.metrics.keys():
            if m in new_data.keys():
                self.__series.data[m] += new_data[m]
        for k, v in attributes.items():
            self.__series.attributes[k].append(v)

        result = {}
        weak_change_points = {}

        for metric in self.__series.data.keys():
            if metric not in new_data:
                weak_change_points[metric] = self.weak_change_points[metric]
                continue

            change_points, weak_cps = compute_change_points(
                self.__series.data[metric],
                window_len=self.options.window_len,
                max_pvalue=self.options.max_pvalue,
                min_magnitude=self.options.min_magnitude,
                new_data=len(new_data[metric]),
                old_weak_cp=self.weak_change_points.get(metric, [])
            )
            result[metric] = []
            for c in change_points:
                result[metric].append(
                    ChangePoint(
                        index=c.index, time=self.__series.time[c.index], metric=metric, stats=c.stats
                    )
                )
            weak_change_points[metric] = []
            for c in weak_cps:
                weak_change_points[metric].append(
                    ChangePoint(
                        index=c.index, time=self.__series.time[c.index], metric=metric, stats=c.stats
                    )
                )
            fill_missing(self.__series.data[metric])

        # If some metrics didn't participate in this round, we still keep them, but update the ones
        # We did recompute
        for metric in result.keys():
            self.change_points[metric] = result[metric]
        for metric in weak_change_points.keys():
            self.weak_change_points[metric] = weak_change_points[metric]
        self.change_points_by_time = self.__group_change_points_by_time(self.__series, self.change_points)
        return result, weak_change_points

    def test_name(self) -> str:
        return self.__series.test_name

    def branch_name(self) -> Optional[str]:
        return self.__series.branch

    def len(self) -> int:
        return len(self.__series.time)

    def time(self) -> List[int]:
        return [int(t) for t in self.__series.time]

    def data(self, metric: str) -> List[float]:
        return [float(d) for d in self.__series.data[metric]]

    def attributes(self) -> Iterable[str]:
        return self.__series.attributes.keys()

    def attributes_at(self, index: int) -> Dict[str, str]:
        return self.__series.attributes_at(index)

    def attribute_values(self, attribute: str) -> List[str]:
        return self.__series.attributes[attribute]

    def metric_names(self) -> Iterable[str]:
        return self.__series.metrics.keys()

    def metric(self, name: str) -> Metric:
        return self.__series.metrics[name]

    def to_json(self):
        change_points_json = {}
        for metric, cps in self.change_points.items():
            change_points_json[metric] = [cp.to_json(rounded=False) for cp in cps]

        weak_change_points_json = {}
        for metric, cps in self.weak_change_points.items():
            weak_change_points_json[metric] = [cp.to_json(rounded=False) for cp in cps]

        data_json = {}
        for metric, datapoints in self.__series.data.items():
            data_json[metric] = [float(d) if d is not None else None for d in datapoints]

        return {
            "test_name": self.test_name(),
            "time": self.time(),
            "change_points_timestamp": self.change_points_timestamp,
            "branch_name": self.branch_name(),
            "options": self.options.to_json(),
            "metrics": self.__series.metrics,
            "attributes": self.__series.attributes,
            "data": self.__series.data,
            "change_points": change_points_json,
            "weak_change_points": weak_change_points_json
        }

    @classmethod
    def from_json(cls, analyzed_json):
        new_metrics = {}

        for metric_name, unit in analyzed_json["metrics"].items():
            new_metrics[metric_name] = Metric(None, None, unit)

        new_series = Series(
            analyzed_json["test_name"],
            analyzed_json["branch_name"],
            analyzed_json["time"],
            new_metrics,
            analyzed_json["data"],
            analyzed_json["attributes"]
        )

        new_options = AnalysisOptions()
        new_options.window_len = analyzed_json["options"]["window_len"]
        new_options.max_pvalue = analyzed_json["options"]["max_pvalue"]
        new_options.min_magnitude = analyzed_json["options"]["min_magnitude"]
        new_options.orig_edivisive = analyzed_json["options"]["orig_edivisive"]

        new_change_points = {}
        for metric, change_points in analyzed_json["change_points"].items():
            new_list = list()
            for cp in change_points:
                stat = ComparativeStats(cp["mean_before"], cp["mean_after"], cp["stddev_before"],
                                        cp["stddev_after"], cp["pvalue"])
                new_list.append(
                    ChangePoint(
                        index=cp["index"], time=cp["time"], metric=cp["metric"], stats=stat
                    )
                )
            new_change_points[metric] = new_list

        new_weak_change_points = {}
        for metric, change_points in analyzed_json.get("weak_change_points", {}).items():
            new_list = list()
            for cp in change_points:
                stat = ComparativeStats(cp["mean_before"], cp["mean_after"], cp["stddev_before"],
                                        cp["stddev_after"], cp["pvalue"])
                new_list.append(
                    ChangePoint(
                        index=cp["index"], time=cp["time"], metric=cp["metric"], stats=stat
                    )
                )
            new_weak_change_points[metric] = new_list

        analyzed_series = cls(new_series, new_options, new_change_points)
        analyzed_series.weak_change_points = new_weak_change_points

        if "change_points_timestamp" in analyzed_json.keys():
            analyzed_series.change_points_timestamp = analyzed_json["change_points_timestamp"]
            analyzed_series.change_points_by_time = AnalyzedSeries.__group_change_points_by_time(analyzed_series.__series, analyzed_series.change_points)

        return analyzed_series


@dataclass
class SeriesComparison:
    series_1: AnalyzedSeries
    series_2: AnalyzedSeries
    index_1: int
    index_2: int
    stats: Dict[str, ComparativeStats]  # keys: metric name


def compare(
    series_1: AnalyzedSeries,
    index_1: Optional[int],
    series_2: AnalyzedSeries,
    index_2: Optional[int],
) -> SeriesComparison:

    # if index not specified, we want to take the most recent performance
    index_1 = index_1 if index_1 is not None else len(series_1.time())
    index_2 = index_2 if index_2 is not None else len(series_2.time())
    metrics = filter(lambda m: m in series_2.metric_names(), series_1.metric_names())

    tester = TTestSignificanceTester(series_1.options.max_pvalue)
    stats = {}

    for metric in metrics:
        data_1 = series_1.data(metric)
        (begin_1, end_1) = series_1.get_stable_range(metric, index_1)
        data_1 = [x for x in data_1[begin_1:end_1] if x is not None]

        data_2 = series_2.data(metric)
        (begin_2, end_2) = series_2.get_stable_range(metric, index_2)
        data_2 = [x for x in data_2[begin_2:end_2] if x is not None]

        stats[metric] = tester.compare(np.array(data_1), np.array(data_2))

    return SeriesComparison(series_1, series_2, index_1, index_2, stats)
