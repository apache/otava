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
from typing import Dict, Iterable, List, Optional

from pydantic import TypeAdapter

from otava.analysis import (
    TTestStats,
    compute_change_points,
    compute_change_points_orig,
)
from otava.change_point_divisive.base import (
    ChangePoint,
    ChangePointGroup,
    ChangePoints,
    ChangePointsByMetric,
    ChangePointsByTime,
)
from otava.serialization import AnalysisOptionsModel, AnalyzedSeriesModel, JsonScalar

_datetime_adapter = TypeAdapter(datetime)


class AnalysisOptions(AnalysisOptionsModel):
    pass


@dataclass
class Metric:
    direction: int
    scale: float
    unit: str

    def __init__(self, direction: int = 1, scale: float = 1.0, unit: str = ""):
        self.direction = direction
        self.scale = scale
        self.unit = unit

    def to_json(self):
        return {"direction": self.direction, "scale": self.scale, "unit": self.unit}


class Series:
    """
    Stores values of interesting metrics of all runs of
    a fallout test indexed by a single time variable.
    Provides utilities to analyze data e.g. find change points.
    """

    test_name: str
    branch: Optional[str]
    time: List[int | float]
    metrics: Dict[str, Metric]
    attributes: Dict[str, List[JsonScalar]]
    data: Dict[str, List[float]]

    def __init__(
        self,
        test_name: str,
        branch: Optional[str],
        time: List[int | float],
        metrics: Dict[str, Metric],
        data: Dict[str, List[float]],
        attributes: Dict[str, List[JsonScalar]],
    ):
        self.test_name = test_name
        self.branch = branch
        self.time = time
        self.metrics = metrics
        self.attributes = attributes if attributes else {}
        self.data = data
        assert all(len(x) == len(time) for x in data.values())
        assert all(len(x) == len(time) for x in attributes.values())

    def attributes_at(self, index: int) -> Dict[str, JsonScalar]:
        result = {}
        for k, v in self.attributes.items():
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

    def analyze(self, options: Optional[AnalysisOptions] = None) -> "AnalyzedSeries":
        if options is None:
            options = AnalysisOptions()
        logging.info(f"Computing change points for test {self.test_name}...")
        return AnalyzedSeries(self, options)


class AnalyzedSeries:
    """
    Time series data with computed change points.

    Change points are computed lazily, on first access. Constructing an
    instance is cheap for callers that never read them.
    """

    __series: Series
    options: AnalysisOptions

    def __init__(
        self, series: Series, options: AnalysisOptions, change_points: Dict[str, ChangePoint] = None
    ):
        self.__series = series
        self.options = options
        self.__change_points = change_points
        self.__weak_change_points = ChangePointsByMetric() if change_points is not None else None
        self.__change_points_by_time = None
        # records when the change points were calculated
        self.__change_points_timestamp = (
            datetime.now(timezone.utc) if change_points is not None else None
        )

    def __ensure_change_points_computed(self):
        if self.__change_points is None:
            cp, weak_cps = self.__compute_change_points(self.__series, self.options)
            self.__change_points = cp
            self.__weak_change_points = weak_cps
            self.__change_points_timestamp = datetime.now(timezone.utc)

    @property
    def change_points(self) -> ChangePointsByMetric:
        self.__ensure_change_points_computed()
        return self.__change_points

    @property
    def weak_change_points(self) -> ChangePointsByMetric:
        self.__ensure_change_points_computed()
        return self.__weak_change_points

    @property
    def change_points_timestamp(self) -> datetime:
        self.__ensure_change_points_computed()
        return self.__change_points_timestamp

    @property
    def change_points_by_time(self) -> ChangePointsByTime:
        if self.__change_points_by_time is None:
            self.__change_points_by_time = self.__group_change_points_by_time(
                self.__series, self.change_points
            )
        return self.__change_points_by_time

    @staticmethod
    def __compute_change_points(
        series: Series, options: AnalysisOptions
    ) -> (ChangePointsByMetric, ChangePointsByMetric):
        # To find change points, go one metric at a time
        result = ChangePointsByMetric()
        weak_change_points = ChangePointsByMetric()
        for metric in series.data.keys():
            values = series.data[metric].copy()
            if options.orig_edivisive:
                change_points, _ = compute_change_points_orig(
                    values,
                    max_pvalue=options.max_pvalue,
                )
                for c in change_points:
                    c.metric = metric
                    cpg = ChangePointGroup(
                        time=series.time[c.index],
                        attributes=series.attributes_at(c.index),
                        changes={metric: c},
                    )
                    result.append(cpg)
            else:
                change_points, weak_cps = compute_change_points(
                    values,
                    window_len=options.window_len,
                    max_pvalue=options.max_pvalue,
                    min_magnitude=options.min_magnitude,
                )
                for c in weak_cps:
                    c.metric = metric
                    cpg = ChangePointGroup(
                        time=series.time[c.index],
                        attributes=series.attributes_at(c.index),
                        changes={metric: c},
                    )
                    weak_change_points.append(cpg)
                for c in change_points:
                    c.metric = metric
                    cpg = ChangePointGroup(
                        time=series.time[c.index],
                        attributes=series.attributes_at(c.index),
                        changes={metric: c},
                    )
                    result.append(cpg)

        return result, weak_change_points

    @staticmethod
    def __group_change_points_by_time(
        series: Series, change_points: ChangePoints
    ) -> ChangePointsByTime:
        return change_points.by_time()

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
        for cp in self.change_points.get_change_points_for_metric(metric):
            if cp.index > index:
                break
            begin = cp.index

        end = len(self.time())
        for cp in reversed(self.change_points.get_change_points_for_metric(metric)):
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
                return ValueError(
                    "time must be monotonously increasing if you use append() time={}".format(time)
                )

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
                weak_change_points[metric] = self.weak_change_points.select_metrics(metric)
                continue

            new_data_len = len(new_data[metric])
            old_weak_cp = [
                cp
                for cp in self.weak_change_points.get_change_points_for_metric(metric)
                if cp.index < len(self.__series.data[metric]) - new_data_len - 1
            ]
            change_points, weak_cps = compute_change_points(
                self.__series.data[metric],
                window_len=self.options.window_len,
                max_pvalue=self.options.max_pvalue,
                min_magnitude=self.options.min_magnitude,
                new_data=new_data_len,
                old_weak_cp=old_weak_cp,
            )
            if metric not in result:
                result[metric] = []
            for c in change_points:
                cp = c.copy()
                cp.metric = metric
                result[metric].append(
                    ChangePointGroup(
                        time=self.__series.time[cp.index],
                        changes={metric: cp},
                        attributes=self.__series.attributes_at(cp.index),
                    )
                )
            if metric not in weak_change_points:
                weak_change_points[metric] = []
            for c in weak_cps:
                cp = c.copy()
                cp.metric = metric
                weak_change_points[metric].append(
                    ChangePointGroup(
                        time=self.__series.time[cp.index],
                        changes={metric: cp},
                        attributes=self.__series.attributes_at(cp.index),
                    )
                )

        r = ChangePointsByMetric.from_dict(result)
        w = ChangePointsByMetric.from_dict(weak_change_points)
        # r has a subset of all metrics, so can't just set change_points to r
        for metric, cpglist in r.items():
            self.change_points[metric] = cpglist
        self.__weak_change_points = w
        self.__change_points_by_time = self.change_points.by_time()
        return r, w

    def test_name(self) -> str:
        return self.__series.test_name

    def branch_name(self) -> Optional[str]:
        return self.__series.branch

    def len(self) -> int:
        return len(self.__series.time)

    def time(self) -> List[int | float]:
        return list(self.__series.time)

    def data(self, metric: str) -> List[float]:
        return [float(d) for d in self.__series.data[metric]]

    def attributes(self) -> Iterable[str]:
        return self.__series.attributes.keys()

    def attributes_at(self, index: int) -> Dict[str, JsonScalar]:
        return self.__series.attributes_at(index)

    def attribute_values(self, attribute: str) -> List[JsonScalar]:
        return self.__series.attributes[attribute]

    def metric_names(self) -> Iterable[str]:
        return self.__series.metrics.keys()

    def metric(self, name: str) -> Metric:
        return self.__series.metrics[name]

    def to_json(self):
        change_points_json = {}
        cpbm = self.change_points.by_metric()
        for metric_name in self.change_points.metrics():
            change_points_json[metric_name] = []
            for cp in cpbm.select_metrics(metric_name):
                change_points_json[metric_name].append(cp.to_json())

        weak_change_points_json = {}
        wcpbm = self.weak_change_points.by_metric()
        for metric_name in self.weak_change_points.metrics():
            weak_change_points_json[metric_name] = []
            for cp in wcpbm.select_metrics(metric_name):
                weak_change_points_json[metric_name].append(cp.to_json())

        data_json = {}
        for metric, datapoints in self.__series.data.items():
            data_json[metric] = [float(d) if d is not None else None for d in datapoints]

        metrics_json = {}
        for metric, unit in self.__series.metrics.items():
            metrics_json[metric] = unit.to_json()

        payload = {
            "test_name": self.test_name(),
            "time": self.time(),
            "change_points_timestamp": self.change_points_timestamp,
            "branch_name": self.branch_name(),
            "options": self.options.model_dump(mode="json"),
            "metrics": metrics_json,
            "attributes": self.__series.attributes,
            "data": data_json,
            "change_points": change_points_json,
            "weak_change_points": weak_change_points_json,
        }
        return AnalyzedSeriesModel.model_validate(payload).model_dump(mode="json")

    @classmethod
    def from_json(cls, analyzed_json):
        def stats_from_json(cp_json):
            return TTestStats(
                mean_1=cp_json["mean_before"],
                mean_2=cp_json["mean_after"],
                std_1=cp_json["stddev_before"],
                std_2=cp_json["stddev_after"],
                pvalue=cp_json["pvalue"],
            )

        def change_point_from_json(metric, cp_json):
            return ChangePoint(
                index=cp_json["index"],
                qhat=cp_json.get("qhat", 0.0),
                metric=cp_json.get("metric") or metric,
                stats=stats_from_json(cp_json),
            )

        def change_points_from_json(change_points_json):
            new_change_points = {}
            for metric, groups in change_points_json.items():
                new_change_points[metric] = []
                for group in groups:
                    if "changes" in group:
                        changes = {
                            cp_json.get("metric") or metric: change_point_from_json(metric, cp_json)
                            for cp_json in group["changes"]
                        }
                        new_change_points[metric].append(
                            ChangePointGroup(
                                time=group["time"],
                                attributes=group["attributes"],
                                changes=changes,
                            )
                        )
                    else:
                        new_change_points[metric].append(
                            ChangePointGroup(
                                time=group["time"],
                                attributes=group.get("attributes", {}),
                                changes={metric: change_point_from_json(metric, group)},
                            )
                        )
            return ChangePointsByMetric.from_dict(new_change_points)

        new_metrics = {}

        for metric_name, metric_json in analyzed_json["metrics"].items():
            if isinstance(metric_json, dict):
                new_metrics[metric_name] = Metric(
                    metric_json.get("direction"),
                    metric_json.get("scale"),
                    metric_json.get("unit", ""),
                )
            else:
                new_metrics[metric_name] = Metric(None, None, metric_json)

        new_series = Series(
            analyzed_json["test_name"],
            analyzed_json["branch_name"],
            analyzed_json["time"],
            new_metrics,
            analyzed_json["data"],
            analyzed_json["attributes"],
        )

        new_options = AnalysisOptions.model_validate(analyzed_json["options"])

        new_change_points = change_points_from_json(analyzed_json["change_points"])
        new_weak_change_points = change_points_from_json(
            analyzed_json.get("weak_change_points", {})
        )

        analyzed_series = cls(new_series, new_options, new_change_points)
        analyzed_series.__weak_change_points = new_weak_change_points

        if "change_points_timestamp" in analyzed_json.keys():
            analyzed_series.__change_points_timestamp = _datetime_adapter.validate_python(
                analyzed_json["change_points_timestamp"]
            )

        return analyzed_series
