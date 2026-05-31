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
"""
Hierarchy of ChangePoint classes:

    CandidateChangePoint   <-->   ChangePoint   --> ChangePointSerializer
      .index                       .index                .to_json()
                               ,   .stats                .get_this_or_that()
                                      ^
                             /         `------BaseStats
                                               ^  .pvalue
                           /                   `
                                                `GenericStats
                         /                       TTestStats
                                                 PermutationStats
                       /
              ChangePointGroup
                 .time
                 .attributes.commit
                 .changes[metric, ChangePoint]
                 # Essentially a row: One or more ChangePoint at the same commit/time

                /
            ChangePoints
               # Typically all change points for a given test / run / etc
            ^
            |
                                                   ^
        ChangePointsByTime                         `ChangePointsByMetric
          .change_points: list(ChangePointGroup)    .change_points: dict[metric, list(ChangePointGroup)]
          .pivot()                         < - - >  .pivot()
"""

from collections import OrderedDict
from dataclasses import dataclass, fields
from datetime import UTC, datetime
from typing import Dict, Generic, List, Optional, TypeVar, Sequence, SupportsFloat, Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class CandidateChangePoint:
    """Candidate for a change point. The point that maximizes Q-hat function on [start:end+1] slice"""

    index: int
    qhat: float


@dataclass
class BaseStats:
    """Abstract statistics class for change point. Implementation depends on the statistical test."""

    # The pvalue for this change point. Exact value depends on the algorithm that was used.
    pvalue: float
    mean_1: float
    mean_2: float
    std_1: float
    std_2: float

    def __init__(self, left: Sequence[SupportsFloat], right: Sequence[SupportsFloat], pvalue=None) -> Any:
        """
        Basic statsistics about the left and right side, and the change between them.

        Calculate basic statistics about the left and right sides of a change point, such as mean
        standard deviation. p-value depeds on the significance test used, so we cannot know or compute
        it here, but if the caller knows p already, they can supply it as argument.
        """
        self.calculate_base_stats(left, right, pvalue)

    def calculate_base_stats(self, left, right, pvalue=None):
        if pvalue is not None and pvalue >= 0.0 and pvalue <= 1.0:
            self.pvalue = pvalue
        else:
            self.pvalue = 1.0

        if len(left) == 0 or len(right) == 0:
            raise ValueError

        self.mean_1 = np.mean(left)
        self.mean_2 = np.mean(right)
        self.std_1 = np.std(left) if len(left) >= 2 else 0.0
        self.std_2 = np.std(right) if len(right) >= 2 else 0.0

        return self

    def forward_rel_change(self, value_if_nan=0):
        """Relative change from left to right"""
        if self.mean_1 == 0:
            return value_if_nan

        return self.mean_2 / self.mean_1 - 1.0

    def backward_rel_change(self, value_if_nan=0):
        """Relative change from right to left"""
        if self.mean_2 == 0:
            return value_if_nan

        return self.mean_1 / self.mean_2 - 1.0

    def forward_change_percent(self) -> float:
        return self.forward_rel_change() * 100.0

    def backward_change_percent(self) -> float:
        return self.backward_rel_change() * 100.0

    def change_magnitude(self):
        """Maximum of absolutes of rel_change and rel_change_reversed"""
        return max(abs(self.forward_rel_change()), abs(self.backward_rel_change()))

    def mean_before(self):
        return self.mean_1

    def mean_after(self):
        return self.mean_2

    def stddev_before(self):
        return self.std_1

    def stddev_after(self):
        return self.std_2

    def to_json(self):
        return {
            "forward_change_percent": f"{self.forward_change_percent():-0f}",
            "magnitude": f"{self.change_magnitude():-0f}",
            "mean_before": f"{self.mean_before():-0f}",
            "stddev_before": f"{self.stddev_before():-0f}",
            "mean_after": f"{self.mean_after():-0f}",
            "stddev_after": f"{self.stddev_after():-0f}",
            "pvalue": f"{self.pvalue:-0f}",
        }

# Abstract variable type for statistics, corresponds to BaseStats class and its subclasses.
GenericStats = TypeVar("GenericStats", bound=BaseStats)


@dataclass
class ChangePoint(CandidateChangePoint, Generic[GenericStats]):
    """
    ChangePoint class.

    Defined by index and signigicance test statistic.
    This class is the basic change point that is used during computation
    and returned as a result. This class does not however carry additional
    attributes like metric, time, or commit sha. Those are in ChangePointGroup
    and ChangePoints.
    Note that while in theory the index, commit sha, an the time(stamp) should
    all be the same, in practice they aren't always. For example if at some point
    during a tests lifetime, more metrics are added to the output, then different
    metrics will have different histories and therefore their indexes start from
    different locations.
    To use time(stamp), metric name or timestamp, to access change points, please
    use the ChangePointGroup and ChangePoints classes.
    """

    stats: GenericStats
    # Which metric this change point belongs to. (This is redundant and for convenience.)
    metric: Optional[str] = None

    def __eq__(self, other):
        """Helpful to identify new Change Points during divisive algorithm"""
        return isinstance(other, self.__class__) and self.index == other.index

    @classmethod
    def from_candidate(
        cls, candidate: CandidateChangePoint, stats: GenericStats
    ) -> "ChangePoint[GenericStats]":
        return cls(
            index=candidate.index,
            qhat=candidate.qhat,
            stats=stats,
        )

    def to_candidate(self) -> CandidateChangePoint:
        """Downgrades Change Point to a Candidate Change Point. Used to recompute stats for Weak Change Points."""
        data = {f.name: getattr(self, f.name) for f in fields(CandidateChangePoint)}
        return CandidateChangePoint(**data)

    def to_json(self, rounded=True):
        cps = ChangePointSerializer(self)
        return cps.to_json(rounded)


class ChangePointSerializer(ChangePoint):
    """
    Utility class with getters and json serialization for a ChangePoint.

    TODO: Maintaining this is tedious. We should replace it with pydantic or some
    other standard solution that provides json serialization.
    """

    def __init__(self, cp: ChangePoint[GenericStats]):
        self.stats = cp.stats
        self.index = cp.index
        self.metric = cp.metric

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

    time: float
    attributes: Dict[str, str]
    # ChangePointGroup.changes.keys() stores the set of metrics that were used at this ChangePointGroup.time.
    changes: Dict[str, ChangePoint]

    def to_json(self, rounded=False):
        changes = []
        for metric, cp in self.changes.items():
            changes.append(cp.to_json(rounded=rounded))

        return {
            "time": self.time,
            "attributes": self.attributes,
            "changes": changes,
        }

    def __getitem__(self, metric):
        return self.changes[metric]

    def metrics(self):
        return self.changes.keys()

    def commit(self, idx: int):
        return self.attribute_at(idx).get("commit")

    def datetime(self):
        return datetime.fromtimestamp(self.time, UTC)

    def select_metrics(self, m: list[str] | str):
        if not isinstance(m, list):
            m = [m]
        filtered = ChangePointGroup(time=self.time, attributes=self.attributes, changes={})
        for metric, cp in self.changes.items():
            if metric in m:
                filtered.changes[metric] = cp
        return filtered

    def set(self, metric: str, cp: ChangePoint):
        self.changes[metric] = cp

    def __iter__(self):
        return iter([v for v in list(self.changes.values())])


class ChangePoints:
    """
    A list of ChangePointGroup objects.

    Typical usage of this would be to hold all the change points over a history of a single test,
    the test producing one or more metrics. Note that this is a sparse structure: It is NOT
    guaranteed that each row (each GhangePointGroup) has each metric. Similarly it is not guaranteed
    that a given metric will hold the full sequence.

    Companion class ChangePointsByMetric is expected to provide functionally equivalent interface, but
    storing each series separately by metric, which is used in parts of the code base, in particular, what
    Series.analyze() returns.
    Subclass ChangePointsByTime is this same class, but can be used if you explicitly want to mark the ordering.
    """

    def __init__(self, cps=None):
        if isinstance(cps, dict) and not isinstance(cps, OrderedDict):
            raise TypeError(
                "ChangePointsByTime doesn't accept a dict() as constructor input. Did you want ChangePointsByMetric()?"
            )
        if isinstance(cps, OrderedDict):
            for k, v in cps.items():
                if not isinstance(k, float):
                    raise TypeError(
                        "ChangePointsByTime with OrderedDict() as constructor input requires the keys to be float (timestamps)?"
                    )
                if not isinstance(v, ChangePointGroup):
                    raise TypeError(
                        "ChangePointsByTime input must be an OrderedDict() of ChangePointGroup objects as values."
                    )
            self.change_points = sorted(cps, key=lambda cpg: cpg.time)
            return
        if cps is None:
            self.change_points = []
            return

        if isinstance(cps, ChangePointsByTime):
            self.change_points = sorted(cps.change_points, key=lambda cpg: cpg.time)
            return
        if isinstance(cps, ChangePointsByMetric):
            self.change_points = cps.pivot().change_points
            return

        if not isinstance(cps, list):
            cps = [cps]
        for obj in sorted(cps, key=lambda cpg: cpg.time):
            if not isinstance(obj, ChangePointGroup):
                t = type(obj)
                raise TypeError(
                    f"ChangePoints() takes as argument one or more ChangePointGroup objects. Got {t}."
                )
        self.change_points = cps

    def append(self, cpg: ChangePointGroup):
        if not isinstance(cpg, ChangePointGroup):
            raise TypeError("ChangePoints.append() takes as argument one ChangePointGroup.")

        if (not self.change_points) or cpg.time > self.change_points[-1].time:
            self.change_points.append(cpg)
        elif self.change_points and cpg.time == self.change_points[-1].time:
            for metric, cp in cpg.changes.items():
                if metric in self.change_points[-1].changes:
                    raise KeyError("Duplicate keys. Shouldn't happen.")
                self.change_points[-1].changes[metric] = cp
        else:
            # TODO: logging
            # print(self.change_points)
            # print(cpg)
            raise ValueError(
                "ChangePoints.append() can only be used such that time is monotonically increasing"
            )

    def extend(self, cps):
        errmsg = "ChangePoints.extend() takes as argument a list of ChangePointGroup objects."
        if not isinstance(cps, list):
            raise TypeError(errmsg)
        for obj in cps:
            if not isinstance(obj, ChangePointGroup):
                raise TypeError(errmsg)
            if (not self.change_points) or obj.time > self.change_points[-1].time:
                self.change_points.append(obj)
            else:
                raise ValueError(
                    "ChangePoints.extend() can only be used such that time is monotonically increasing"
                )

    def items(self):
        return self.pivot().items()

    def __iter__(self):
        return iter(self.change_points)

    def __len__(self):
        return len(self.change_points)

    def __getitem__(self, n):
        return self.change_points[n]

    def metrics(self) -> set:
        all_metrics = set()
        for row in self.change_points:
            all_metrics.add(row.metrics())
        return all_metrics

    def select_metrics(self, m: list[str] | str):
        """
        Get a new ChangePoints object holding only the given metric(s).

        If you think of a ChangePoints object as timestamps being rows, and
        the metrics being columns, then this returns a single column.

        Note: The internal data structure doesn't do anything to make this
        request efficient. This will loop over all ChangePointGroups.
        Use ChangePointsByMetric if you need this to be fast.
        """
        filtered = ChangePoints()
        for cpg in self.change_points:
            filtered.append(cpg.select_metrics(m))
        return filtered

    def get_change_points_for_metric(self, m: str):
        single_metric = self.select_metrics(m)
        return [list(cpg.changes.values())[0] for cpg in single_metric.change_points]

    def at_timestamp(self, t: float):
        for cpg in self.change_points:
            if cpg.time == t:
                return cpg
            if abs(cpg.time - t) < 0.0001:
                return cpg
        raise LookupError(t)

    def at_commit(self, sha: str):
        for row in self:
            if row.attributes['commit'] == sha:
                return row
        raise LookupError(sha)

    def pivot(self):
        """
        Return the same object as ChangePointsByMetric.
        """
        by_metric = ChangePointsByMetric()

        for row in sorted(self.change_points, key=lambda cpg: cpg.time):
            assert isinstance(row, ChangePointGroup)
            # append() does the necessary shuffling into separate columns
            by_metric.append(row)


class ChangePointsByTime(ChangePoints):
    pass


class ChangePointsByMetric(ChangePoints):
    """
    Provides same interface as ChangePoints, but internally stores with metric first.
    """

    def __init__(self, cps=None):
        if isinstance(cps, ChangePointsByMetric):
            self.change_points = cps.change_points
        if isinstance(cps, ChangePointsByTime):
            self.change_points = cps.pivot().change_points

        if cps is None:
            self.change_points = OrderedDict()
            return
        if isinstance(cps, list):
            cpm = []
            for obj in sorted(cps, key=lambda cpg: cpg.time):
                if not isinstance(obj, ChangePointGroup):
                    t = type(obj)
                    raise TypeError(
                        f"ChangePointsByMetric() takes as input a list of ChangePointGroup objects. Got {t}."
                    )
                cpm.append(obj)

            self.change_points = cpm
        if isinstance(cps, dict):
            # We actually don't need the ordering in this case, but we want the type to match the other class
            self.change_points = OrderedDict()
            for metric, cpglist in cps.items():
                for cpg in cpglist:
                    if not isinstance(cpg, ChangePointGroup):
                        raise TypeError(
                            "ChangePointsByMetric takes as constructor argument a dict of ChangePointGroup objects: dict[str, list[ChangePointGroup]]"
                        )
                self.change_points[metric] = sorted(cpglist, key=lambda cpg: cpg.time)

    def pivot(self):
        # Now we pivot (metric,time) to (time,metric) so that we return ChangePoints() objects
        intermediate = []
        for metric, points in self.change_points.items():
            for cpg in sorted(points, key=lambda cpg: cpg.time):
                assert isinstance(cpg, ChangePointGroup)
                intermediate.append(cpg)
        cp_by_time = ChangePointsByTime()
        for cpg in sorted(intermediate, key=lambda cpg: cpg.time):
            cp_by_time.append(cpg)
        return cp_by_time

    def append(self, cpg: ChangePointGroup):
        if not isinstance(cpg, ChangePointGroup):
            raise TypeError("ChangePoints.append() takes as argument one ChangePointGroup.")
        for metric in cpg.metrics():
            self.change_points[metric].append(cpg.select_metrics(metric))

    def extend(self, cps):
        errmsg = "ChangePoints.extend() takes as argument a list of ChangePointGroup objects."
        if not isinstance(cps, list):
            raise TypeError(errmsg)
        for obj in cps:
            if not isinstance(obj, ChangePointGroup):
                raise TypeError(errmsg)
            self.append(obj)

    def items(self):
        return self.change_points.items()

    def __iter__(self):
        return self.pivot().__iter__()

    def __len__(self):
        return max([len(cpg) for metric, cpg in self.change_points.items()])

    def __getitem__(self, n):
        if not isinstance(n, int):
            raise KeyError("n must be integer index")
        cpgrow = [cpg[n] for metric, cpg in self.change_points.items() if len(cpg) > n]
        if not cpgrow:
            KeyError(f"Nice try {n}. This ChangePoints object only has {len(self)} items.")
        cpg = None
        for c in cpgrow:
            if cpg is None:
                # First element
                cpg = c
                continue
            for metric in cpg.metrics():
                cpg[metric] = c

        return cpg

    def metrics(self):
        return set(self.change_points.keys())

    def select_metrics(self, m: list[str] | str):
        """
        Get a new ChangePoints object holding only the given metric(s).
        """
        if not isinstance(m, list):
            if not isinstance(m, str):
                TypeError("ChangePoints.select_metrics() takes as argument a str or a list of str.")
            m = [m]

        filtered = ChangePointsByMetric()
        for metric in m:
            filtered.change_points[metric] = self.change_points[metric]
        return filtered

    def get_change_points_for_metric(self, m: str):
        single_metric = self.select_metrics(m)
        metric_change_points = []
        for metric, cpg in single_metric.change_points.items():
            for c in cpg:
                metric_change_points.append(c.changes[metric])
        return metric_change_points

    def at_timestamp(self, t: float):
        """
        This is slow, please consider using ChangePointsByTime instead.
        """
        return self.pivot().at_timestamp(t)

    def at_commit(self, sha: str):
        """
        This is slow, please consider using ChangePointsByTime instead.
        """
        return self.pivot().at_commit(sha)


class SignificanceTester(Generic[GenericStats]):
    """Abstract class for significance tester"""

    def __init__(self, max_pvalue: float):
        self.max_pvalue = max_pvalue

    def compare(self, left: Sequence[SupportsFloat], right: Sequence[SupportsFloat], p: float = None) -> GenericStats:
        if len(left) == 0 or len(right) == 0:
            raise ValueError
        return BaseStats(left, right, p)


    def get_sides(
            self, candidate: CandidateChangePoint, series: Sequence[SupportsFloat], intervals: List[slice]
        ) -> (Sequence, Sequence):
        """
        Computes properties of the change point if the Candidate Change Point based on the provided intervals.

        The method works in both steps of the algorithm:
        1. Split step:
           if the candidate is a new potential change point, i.e., its index is inside any interval, then
           we split the interval by the candidate's index to get left and right subseries.
        2. Merge step:
           if the candidate is an existing change point, i.e., it matches the end of two intervals, then
           it's a potential weak change point, and we don't need to split the intervals anymore (just take
           both intervals as left and right subseries).

        """
        for i, interval in enumerate(intervals):
            if interval.stop == candidate.index:
                # Merge step
                left_interval = interval
                right_interval = intervals[i + 1]
                break
            elif (interval.start is None or interval.start < candidate.index) and (interval.stop is None or candidate.index < interval.stop):
                # Split step
                # Note: handles slices with omitted indexes:
                #
                #       array[0 : i] == array[:i] == array[slice(None, i)] == array[slice(0, i)],
                #       i.e., interval.start == None and interval.start == 0 are equivalent.
                #
                #       array[i: len(array)] == array[i:] == array[slice(i, None)] == array[slice(i, len(array))],
                #       i.e., interval.stop == None and interval.stop == len(array) are equivalent.
                left_interval = slice(interval.start, candidate.index)
                right_interval = slice(candidate.index, interval.stop)
                break
        else:
            raise ValueError(
                f"Candidate Change Point at index={candidate.index} doesn't correspond to any interval in {intervals}."
            )
        left = series[left_interval]
        right = series[right_interval]
        return left, right


    def get_intervals(self, change_points: List[ChangePoint[GenericStats]]) -> List[slice]:
        """Returns list of slices of the series. Change points must be sorted by index."""
        assert all(
            change_points[i].index <= change_points[i + 1].index
            for i in range(len(change_points) - 1)
        ), "Change points must be sorted by index"
        intervals = [
            slice(
                0 if i == 0 else change_points[i - 1].index,
                None if i == len(change_points) else change_points[i].index,
            )
            for i in range(len(change_points) + 1)
        ]
        return [interval for interval in intervals if interval.start != interval.stop]

    def is_significant(self, point: ChangePoint[GenericStats]) -> bool:
        """Compares ChangePoint to level of significance max_pvalue"""
        return point.stats.pvalue <= self.max_pvalue

    def change_point(
        self, candidate: CandidateChangePoint, series: NDArray, intervals: List[slice]
    ) -> ChangePoint[GenericStats]:
        """Computes stats for a change point candidate and wraps it into ChangePoint class"""
        ...

class Calculator:
    """Abstract class for calculator. Calculator provides an interface to get best change point candidate"""

    def __init__(self, series: NDArray):
        self.series = series

    def get_next_candidate(self, intervals: List[slice]) -> Optional[CandidateChangePoint]:
        """Returns list of existing change points to find next best change point candidate."""
        candidates = [
            self.get_candidate_change_point(interval=interval)
            for interval in intervals
            if len(self.series[interval]) > 1
        ]
        if not candidates:
            return
        candidate = max(candidates, key=lambda point: point.qhat)
        return candidate

    def get_candidate_change_point(self, interval: slice) -> CandidateChangePoint:
        """Given start and end indexes return best candidate for a change point.
        Note that start and end are indexes of the first and last element, i.e. a slice [start:end+1]."""
        ...
