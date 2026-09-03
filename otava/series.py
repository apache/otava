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
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional
from warnings import warn

from pydantic import (
    BaseModel,
    ConfigDict,
    PrivateAttr,
    TypeAdapter,
    field_validator,
    model_serializer,
    model_validator,
)

from otava.analysis import (
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

JsonScalar = str | int | float | bool | None
_datetime_adapter = TypeAdapter(datetime)


class DomainModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True, arbitrary_types_allowed=True, extra="forbid")


class AnalysisOptions(DomainModel):
    window_len: int = 50
    max_pvalue: float = 0.001
    min_magnitude: float = 0.0
    orig_edivisive: bool = False


class Metric(DomainModel):
    direction: Optional[int] = 1
    scale: Optional[float] = 1.0
    unit: str

    def __init__(self, direction: int = 1, scale: float = 1.0, unit: str = ""):
        super().__init__(direction=direction, scale=scale, unit=unit)

    def to_json(self):
        warn("Metric.to_json() is deprecated; use model_dump(mode='json')", DeprecationWarning, stacklevel=2)
        return self.model_dump(mode="json")


class Series(DomainModel):
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
    data: Dict[str, List[Optional[float]]]

    def __init__(
        self,
        test_name: str,
        branch: Optional[str] = None,
        time: Optional[List[int | float]] = None,
        metrics: Optional[Dict[str, Metric]] = None,
        data: Optional[Dict[str, List[Optional[float]]]] = None,
        attributes: Optional[Dict[str, List[JsonScalar]]] = None,
    ):
        super().__init__(
            test_name=test_name,
            branch=branch,
            time=[] if time is None else time,
            metrics={} if metrics is None else metrics,
            data={} if data is None else data,
            attributes={} if attributes is None else attributes,
        )
        # append() historically extends the caller-provided timeline in place.
        # Keep that mutation behaviour while validation continues to happen at construction/assignment.
        if time is not None:
            time[:] = self.time
            object.__setattr__(self, "time", time)

    @field_validator("time")
    @classmethod
    def validate_timestamps(cls, value):
        if any(isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)) for timestamp in value):
            raise ValueError("time values must be numeric")
        return value

    @model_validator(mode="after")
    def validate_structure(self):
        expected_length = len(self.time)
        if self.metrics and set(self.data) != set(self.metrics):
            raise ValueError("data and metrics must have the same metric names")
        if any(len(values) != expected_length for values in self.data.values()):
            raise ValueError("all data series must align with time")
        if any(len(values) != expected_length for values in self.attributes.values()):
            raise ValueError("all attribute series must align with time")
        return self

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
        return AnalyzedSeries(self, options)


class AnalyzedSeries(DomainModel):
    """
    Time series data with computed change points.
    """

    series: Series
    options: AnalysisOptions
    _change_points: Optional[ChangePointsByMetric] = PrivateAttr(default=None)
    _weak_change_points: Optional[ChangePointsByMetric] = PrivateAttr(default=None)
    _change_points_by_time: Optional[ChangePointsByTime] = PrivateAttr(default=None)
    _change_points_timestamp: Optional[datetime] = PrivateAttr(default=None)

    def __init__(
        self,
        series: Series,
        options: Optional[AnalysisOptions] = None,
        change_points: Optional[ChangePointsByMetric] = None,
        weak_change_points: Optional[ChangePointsByMetric] = None,
        change_points_timestamp: Optional[datetime] = None,
    ):
        super().__init__(series=series, options=options or AnalysisOptions())
        self._change_points = change_points
        self._weak_change_points = (
            weak_change_points if weak_change_points is not None else ChangePointsByMetric()
        ) if change_points is not None else None
        self._change_points_timestamp = (
            change_points_timestamp or datetime.now(timezone.utc)
            if change_points is not None
            else None
        )

    def __ensure_change_points_computed(self):
        if self._change_points is None:
            logging.info(f"Computing change points for test {self.series.test_name}...")
            self._change_points, self._weak_change_points = self.__compute_change_points(
                self.series, self.options
            )
            self._change_points_timestamp = datetime.now(timezone.utc)

    @property
    def change_points(self) -> ChangePointsByMetric:
        self.__ensure_change_points_computed()
        return self._change_points

    @change_points.setter
    def change_points(self, value: Optional[ChangePointsByMetric]):
        self._change_points = value
        self._change_points_by_time = None

    @property
    def weak_change_points(self) -> ChangePointsByMetric:
        self.__ensure_change_points_computed()
        return self._weak_change_points

    @weak_change_points.setter
    def weak_change_points(self, value: ChangePointsByMetric):
        self._weak_change_points = value

    @property
    def change_points_timestamp(self) -> datetime:
        self.__ensure_change_points_computed()
        return self._change_points_timestamp

    @property
    def change_points_by_time(self) -> ChangePointsByTime:
        if self._change_points_by_time is None:
            self._change_points_by_time = self.__group_change_points_by_time(
                self.series, self.change_points
            )
        return self._change_points_by_time

    @classmethod
    def _parse_persistence_document(cls, value):
        def parse_changes(by_metric):
            result = {}
            for metric, groups in by_metric.items():
                parsed_groups = []
                for group in groups:
                    changes = {}
                    for raw_change in group.get("changes", [group]):
                        change_metric = raw_change.get("metric") or metric
                        stats = raw_change.get("stats") or {
                            "mean_1": raw_change["mean_before"],
                            "mean_2": raw_change["mean_after"],
                            "std_1": raw_change["stddev_before"],
                            "std_2": raw_change["stddev_after"],
                            "pvalue": raw_change["pvalue"],
                        }
                        changes[change_metric] = ChangePoint(
                            index=raw_change["index"],
                            qhat=raw_change.get("qhat", 0.0),
                            metric=change_metric,
                            stats=stats,
                        )
                    parsed_groups.append(
                        ChangePointGroup(
                            time=group["time"], attributes=group.get("attributes", {}), changes=changes
                        )
                    )
                result[metric] = parsed_groups
            return ChangePointsByMetric.from_dict(result)

        metrics = {
            name: Metric(unit=metric) if isinstance(metric, str) else Metric.model_validate(metric)
            for name, metric in value["metrics"].items()
        }
        return {
            "series": Series(
                value["test_name"],
                value.get("branch_name"),
                value["time"],
                metrics,
                value["data"],
                value.get("attributes", {}),
            ),
            "options": value.get("options", {}),
            "change_points": parse_changes(value.get("change_points", {})),
            "weak_change_points": parse_changes(value.get("weak_change_points", {})),
            "change_points_timestamp": _datetime_adapter.validate_python(
                value.get("change_points_timestamp", datetime.now(timezone.utc))
            ),
        }

    @model_validator(mode="wrap")
    @classmethod
    def validate_persistence_document(cls, value, handler):
        """Accept both the domain representation and the historical flat document."""
        if isinstance(value, dict) and "test_name" in value:
            parsed = cls._parse_persistence_document(value)
            return cls(
                parsed["series"],
                AnalysisOptions.model_validate(parsed["options"]),
                parsed["change_points"],
                parsed["weak_change_points"],
                parsed["change_points_timestamp"],
            )
        return handler(value)

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
        # appending updates the cached results, so they must exist first
        self.__ensure_change_points_computed()
        if not isinstance(time, list):
            return ValueError("time argument must be an array.")
        if not isinstance(new_data, dict):
            return ValueError("new_data argument must be a dict with metrics as key.")
        if len(new_data.keys()) == 0 or len([v for v in [vv for vv in new_data.values()]]) == 0:
            return ValueError("new_data argument doesn't contain any data")
        if not isinstance(attributes, dict):
            return ValueError("attributes must be a dict.")

        max_time = max(self.series.time)
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
            self.series.time.append(t)
        for m in self.series.metrics.keys():
            if m in new_data.keys():
                self.series.data[m] += new_data[m]
        for k, v in attributes.items():
            self.series.attributes[k].append(v)

        result = {}
        weak_change_points = {}

        for metric in self.series.data.keys():
            if metric not in new_data:
                if metric in self.weak_change_points:
                    weak_change_points[metric] = self.weak_change_points.select_metrics(metric)
                continue

            new_data_len = len(new_data[metric])
            previous_weak_cp = (
                self.weak_change_points.get_change_points_for_metric(metric)
                if metric in self.weak_change_points
                else []
            )
            old_weak_cp = [
                cp
                for cp in previous_weak_cp
                if cp.index < len(self.series.data[metric]) - new_data_len - 1
            ]
            change_points, weak_cps = compute_change_points(
                self.series.data[metric],
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
                        time=self.series.time[cp.index],
                        changes={metric: cp},
                        attributes=self.series.attributes_at(cp.index),
                    )
                )
            if metric not in weak_change_points:
                weak_change_points[metric] = []
            for c in weak_cps:
                cp = c.copy()
                cp.metric = metric
                weak_change_points[metric].append(
                    ChangePointGroup(
                        time=self.series.time[cp.index],
                        changes={metric: cp},
                        attributes=self.series.attributes_at(cp.index),
                    )
                )

        r = ChangePointsByMetric.from_dict(result)
        w = ChangePointsByMetric.from_dict(weak_change_points)
        # r has a subset of all metrics, so can't just set change_points to r
        for metric, cpglist in r.items():
            self.change_points[metric] = cpglist
        self._weak_change_points = w
        # invalidate rather than rebuild: the property recomputes it on first read
        self._change_points_by_time = None
        self._change_points_timestamp = datetime.now(timezone.utc)
        return r, w

    def test_name(self) -> str:
        return self.series.test_name

    def branch_name(self) -> Optional[str]:
        return self.series.branch

    def len(self) -> int:
        return len(self.series.time)

    def time(self) -> List[int | float]:
        return list(self.series.time)

    def data(self, metric: str) -> List[Optional[float]]:
        return [float(d) if d is not None else None for d in self.series.data[metric]]

    def attributes(self) -> Iterable[str]:
        return self.series.attributes.keys()

    def attributes_at(self, index: int) -> Dict[str, JsonScalar]:
        return self.series.attributes_at(index)

    def attribute_values(self, attribute: str) -> List[JsonScalar]:
        return self.series.attributes[attribute]

    def metric_names(self) -> Iterable[str]:
        return self.series.metrics.keys()

    def metric(self, name: str) -> Metric:
        return self.series.metrics[name]

    @model_serializer(mode="plain")
    def serialize_persistence_document(self, info):
        change_points_json = {}
        cpbm = self.change_points.by_metric() if self.change_points else ChangePointsByMetric()
        for metric_name in cpbm.metrics():
            change_points_json[metric_name] = []
            for cp in cpbm.select_metrics(metric_name):
                change_points_json[metric_name].append(
                    {
                        "time": cp.time,
                        "attributes": cp.attributes,
                        "changes": [change.persistence_dict() for change in cp.changes.values()],
                    }
                )

        weak_change_points_json = {}
        wcpbm = self.weak_change_points.by_metric()
        for metric_name in self.weak_change_points.metrics():
            weak_change_points_json[metric_name] = []
            for cp in wcpbm.select_metrics(metric_name):
                weak_change_points_json[metric_name].append(
                    {
                        "time": cp.time,
                        "attributes": cp.attributes,
                        "changes": [change.persistence_dict() for change in cp.changes.values()],
                    }
                )

        data_json = {}
        for metric, datapoints in self.series.data.items():
            data_json[metric] = [float(d) if d is not None else None for d in datapoints]

        metrics_json = {}
        for metric, unit in self.series.metrics.items():
            metrics_json[metric] = unit.model_dump(mode="json")

        payload = {
            "test_name": self.test_name(),
            "time": self.time(),
            "change_points_timestamp": _datetime_adapter.dump_python(self.change_points_timestamp, mode=info.mode),
            "branch_name": self.branch_name(),
            "options": self.options.model_dump(mode="json"),
            "metrics": metrics_json,
            "attributes": self.series.attributes,
            "data": data_json,
            "change_points": change_points_json,
            "weak_change_points": weak_change_points_json,
        }
        if info.include is not None:
            payload = {key: value for key, value in payload.items() if key in info.include}
        if info.exclude is not None:
            payload = {key: value for key, value in payload.items() if key not in info.exclude}
        return payload

    def to_json(self):
        warn("AnalyzedSeries.to_json() is deprecated; use model_dump(mode='json')", DeprecationWarning, stacklevel=2)
        return self.model_dump(mode="json")

    @classmethod
    def from_json(cls, analyzed_json):
        warn("AnalyzedSeries.from_json() is deprecated; use model_validate()", DeprecationWarning, stacklevel=2)
        return cls.model_validate(analyzed_json)
