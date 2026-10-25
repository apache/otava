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

import copy
from dataclasses import dataclass, replace
from typing import List, Optional, Sequence, SupportsFloat, Tuple

import numpy as np
from scipy.stats import ttest_ind_from_stats

from otava.change_point_divisive.base import (
    BaseStats,
    ChangePoint,
    GenericStats,
    SignificanceTester,
    SplitCandidate,
)
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector
from otava.change_point_divisive.significance_test import (
    PermutationsSignificanceTester,
    PermutationStats,
)


@dataclass
class TTestStats(BaseStats):
    """
    Statistics related to the calculation of a two-sided Student's T-test.

    Note that p-value is already in BaseStats.
    """
    tstatistic: float = 0.0
    degrees_of_freedom: int = 0

    def copy(self):
        # replace() preserves the subclass
        return replace(self)

    def to_json(self):
        obj = super().to_json()
        obj["tstatistic"] = self.tstatistic
        obj["degrees_of_freedom"] = self.degrees_of_freedom
        return obj


# Generic Change Point List
GenCPList = List[ChangePoint[GenericStats]]
# Permutation Change Point List
PermCPList = List[ChangePoint[PermutationStats]]
# T-test Change Point List
TtestCPList = List[ChangePoint[TTestStats]]


# TODO: Move to change_point_divisive.significance_test
class TTestSignificanceTester(SignificanceTester[TTestStats]):
    """
    Uses two-sided Student's T-test to decide if a candidate change point
    splits the series into pieces that are significantly different from each other.
    This test is good if the data between the change points have normal distribution.
    It works well even with tiny numbers of points (<10).
    """

    def compare(self, left: Sequence[SupportsFloat], right: Sequence[SupportsFloat]) -> TTestStats:
        # defaults
        p = 1.0
        t = 0.0

        base_stats = super().compare(left, right)
        df = len(left) + len(right) - 2
        # While "degrees of freedom" is a parameter that is here coming out of the use of T-Test,
        # this is actually the same requirement as can be expressed more intuitively as:
        # We need at least 3 data points to find a statistically significant change point.
        # This is because if we had only 2 points, they can be either equal or different, but if they
        # are different, we have no context for how different they have to be to be statistically significant.
        if df > 0:
            (t, p) = ttest_ind_from_stats(
                base_stats.mean_1, base_stats.std_1, len(left), base_stats.mean_2, base_stats.std_2, len(right), alternative="two-sided"
            )

        return TTestStats(pvalue=p, mean_1=base_stats.mean_1, mean_2=base_stats.mean_2, std_1=base_stats.std_1, std_2=base_stats.std_2, tstatistic=t, degrees_of_freedom=df)

    def evaluate_candidate(
        self,
        candidate: SplitCandidate,
        series: Sequence[SupportsFloat],
        intervals: List[slice],
    ) -> ChangePoint[TTestStats]:
        left, right = self.get_sides(candidate.index, series, intervals)
        stats = self.compare(left, right)
        return ChangePoint.from_candidate(candidate, stats)

    def recompute_change_point(
        self,
        point: ChangePoint[TTestStats],
        series: Sequence[SupportsFloat],
        intervals: List[slice],
    ) -> ChangePoint[TTestStats]:
        left, right = self.get_sides(point.index, series, intervals)
        return ChangePoint(
            index=point.index, qhat=point.qhat, stats=self.compare(left, right), metric=point.metric
        )


class DeterministicTTestSignificanceTester(TTestSignificanceTester):
    """Test the samples selected by Q-hat, ending the right sample at kappa.

    Recomputing an existing point still uses its current neighboring segments.
    """

    def evaluate_candidate(
        self,
        candidate: SplitCandidate,
        series: Sequence[SupportsFloat],
        intervals: List[slice],
    ) -> ChangePoint[TTestStats]:
        for interval in intervals:
            start = 0 if interval.start is None else interval.start
            end = len(series) if interval.stop is None else interval.stop
            if start < candidate.index < end:
                if not candidate.index < candidate.kappa <= min(end, len(series)):
                    raise ValueError("Candidate kappa must lie within the containing interval")
                left = series[start : candidate.index]
                right = series[candidate.index : candidate.kappa]
                return ChangePoint.from_candidate(candidate, self.compare(left, right))
        raise ValueError(f"Split candidate at index={candidate.index} is not inside an interval")


def merge(
    change_points: TtestCPList, series: Sequence[SupportsFloat], max_pvalue: float, min_magnitude: float
) -> TtestCPList:
    """
    Merge step of the change point detection process from "Hunter: Using Change Point Detection
    to Hunt for Performance Regressions" by Fleming et al. (https://doi.org/10.1145/3578244.3583719).

    Parameters:
        :param max_pvalue: maximum accepted pvalue
        :param min_magnitude: minimum accepted relative change
    """
    tester = TTestSignificanceTester(max_pvalue)
    while change_points:
        # Select the change point with weakest unacceptable P-value
        # If all points have acceptable P-values, select the change-point with
        # the least relative change:
        weakest_cp = max(change_points, key=lambda c: c.stats.pvalue)
        if weakest_cp.stats.pvalue < max_pvalue:
            weakest_cp = min(change_points, key=lambda c: c.stats.change_magnitude())
            if weakest_cp.stats.change_magnitude() > min_magnitude:
                return change_points

        # Remove duplicate change points from the list (that is, at same index)
        weakest_cp_index = None
        for i, cp in enumerate(change_points):
            if cp.index == weakest_cp.index:
                weakest_cp_index = i
                break
        assert weakest_cp_index is not None
        del change_points[weakest_cp_index]

        # We can't continue yet, because by removing a change_point
        # the adjacent change points changed their properties.
        # Recompute the adjacent change point stats:
        intervals = tester.get_intervals(change_points)

        def recompute(index: int):
            if index < 0 or index >= len(change_points):
                return
            cp = change_points[index]
            change_points[index] = tester.recompute_change_point(cp, series, intervals)

        recompute(weakest_cp_index)
        recompute(weakest_cp_index + 1)

    return change_points


def split(series: Sequence[SupportsFloat], window_len: int = 30, max_pvalue: float = 0.001,
          new_points: Optional[int] = None, old_cp: Optional[TtestCPList] = None) -> TtestCPList:
    """
    Split step of the change point detection process from "Hunter: Using Change Point Detection
    to Hunt for Performance Regressions" by Fleming et al. (https://doi.org/10.1145/3578244.3583719).
    """
    assert window_len >= 2, "Window length must be at least 2"
    start = 0
    step = int(window_len / 2)
    change_points = []
    # N new_points are appended to the end of series. Typically N=1.
    # old_cp are the weak change points from before new points were added.
    # We now just identify change points in the tail of the series, beginning at
    # max(old_cp[-1], a step that is over 2 window_len from the end)
    if new_points is not None and old_cp is not None:
        change_points = old_cp[:]
        steps_needed = new_points/window_len + 4
        max_start = len(series) - steps_needed*window_len
        for c in old_cp:
            if c.index < max_start:
                start = c.index
        for s in range(0, len(series), step):
            if s < max_start and start < s:
                start = s

    tester = TTestSignificanceTester(max_pvalue)
    while start < len(series):
        # Sliding window series[start : end]
        end = min(start + window_len, len(series))

        algo = ChangePointDetector(significance_tester=tester, calculator=PairDistanceCalculator)
        new_change_points = algo.get_change_points(series, start, end)
        last_new_change_point_index = new_change_points[-1].index if new_change_points else 0
        start = max(last_new_change_point_index, start + step)
        # incremental Otava can duplicate an old cp
        cpindexes = [cp.index for cp in change_points]
        for cp in new_change_points:
            if cp.index not in cpindexes:
                change_points += [cp]
                cpindexes += [cp.index]

    # Sort change points by index; required by get_intervals() and maintained by merge()
    change_points.sort(key=lambda cp: cp.index)
    intervals = tester.get_intervals(change_points)
    return [tester.recompute_change_point(cp, series, intervals) for cp in change_points]


def compute_change_points_orig(series: Sequence[SupportsFloat], max_pvalue: float = 0.001, seed: Optional[int] = None) -> Tuple[PermCPList, Optional[PermCPList]]:
    """
    The original algorithm presented in "A Nonparametric Approach for Multiple Change Point
    Analysis of Multivariate Data" by Matteson and James (https://doi.org/10.48550/arXiv.1306.4933).

    The algorithm recursively splits the series in a way to maximize some measure of dissimilarity (denoted qhat)
    between the chunks. Splitting happens as long as the dissimilarity is statistically significant.
    """
    tester = PermutationsSignificanceTester(max_pvalue=max_pvalue, permutations=100, calculator=PairDistanceCalculator, seed=seed)
    detector = ChangePointDetector(significance_tester=tester, calculator=PairDistanceCalculator)
    change_points = detector.get_change_points(series=series)
    return change_points, None


def compute_change_points_deterministic(series: Sequence[SupportsFloat], max_pvalue: float = 0.001, min_magnitude: float = 0.0) -> Tuple[PermCPList, Optional[PermCPList]]:
    """
    Same as the original algorithm but with deterministic Student T significance test at the end.

    max_pvalue applies to discovery tests using the selected kappa. Returned statistics,
    including p-values, describe the final adjacent segments and may differ from the
    discovery tests. They are not used to apply the discovery cutoff a second time.

    Magnitude filtering removes the smallest current change below min_magnitude,
    recomputes its two neighbors, and repeats until all retained points meet the
    inclusive threshold. The second result contains all discovered points with
    statistics for the unfiltered segmentation.

    The motivation for this variation follows from fixing the bug explained at the top of https://github.com/apache/otava/pull/96
    The intuition is that the split-merge approach introduced by Datastax is addressing the same problem that the _kappa_ variable
    does in the original paper. Now that we compute correctly over all values of kappa, the split-merge part should be unnecessary,
    as the original algorithm with kappa bug fixed, will find the same change points, and more. Therefore the conclusion is we want
    to go back as much as possible to the original and real algorithm from the Matteson & James paper. But even then, we find that
    Student T as significance test is both much faster but also qualitatively produces better results for the use case we're in at least,
    that we want to continue using T test and not random permutations for the significance test.

    TBD: Whether weak change points are still helpful or not. By reading the problem they fix appears unrelated from the split-merge vs **kappa** symptoms.

    TODO: Support incremental e-divisive. This was easy to implement on top of the split-merge variation. Not clear what is the correct way here.
    An easy solution is to rerun from the last change-point, but the problem is the last change point could itself be influenced by the new data
    appended.
    """
    if not isinstance(series, np.ndarray):
        series = np.array(series, dtype=np.float64)
    if not np.issubdtype(series.dtype, np.floating):
        series = series.astype(np.float64, copy=False)
    tester = DeterministicTTestSignificanceTester(max_pvalue=max_pvalue)
    detector = ChangePointDetector(significance_tester=tester, calculator=PairDistanceCalculator)
    all_change_points = detector.get_change_points(series=series)
    intervals = tester.get_intervals(all_change_points)
    all_change_points = [
        tester.recompute_change_point(cp, series, intervals) for cp in all_change_points
    ]
    above_threshold_change_points = all_change_points.copy()
    while min_magnitude > 0.0 and above_threshold_change_points:
        weakest_index = min(
            range(len(above_threshold_change_points)),
            key=lambda i: above_threshold_change_points[i].stats.change_magnitude(),
        )
        if above_threshold_change_points[weakest_index].stats.change_magnitude() >= min_magnitude:
            break
        del above_threshold_change_points[weakest_index]
        intervals = tester.get_intervals(above_threshold_change_points)
        # Removing a boundary joins its segments, changing the comparisons on both sides.
        for index in (weakest_index - 1, weakest_index):
            if 0 <= index < len(above_threshold_change_points):
                above_threshold_change_points[index] = tester.recompute_change_point(
                    above_threshold_change_points[index], series, intervals
                )
    return above_threshold_change_points, all_change_points


def compute_change_points_split(
    series: Sequence[SupportsFloat], window_len: int = 50, max_pvalue: float = 0.001, min_magnitude: float = 0.0,
    new_data: Optional[int] = None, old_weak_cp: Optional[GenCPList] = None
) -> Tuple[GenCPList, Optional[GenCPList]]:
    """
    This function added mainly for symmetry and anticipating a future where this is no longer the default
    """
    return compute_change_points(series, window_len, max_pvalue, min_magnitude, new_data, old_weak_cp)


def compute_change_points(
    series: Sequence[SupportsFloat], window_len: int = 50, max_pvalue: float = 0.001, min_magnitude: float = 0.0,
    new_data: Optional[int] = None, old_weak_cp: Optional[GenCPList] = None
) -> Tuple[GenCPList, Optional[GenCPList]]:
    """
    Change Point detection algorithm described in "Hunter: Using Change Point Detection to Hunt for Performance
    Regressions" by Fleming et al. (https://doi.org/10.1145/3578244.3583719).

    The algorithm consist of two steps:
        1. Split step:
            - splitting a series into subseries via sliding windows

            - applying original change point detection algorithm to each window (https://doi.org/10.48550/arXiv.1306.4933)
              with first-pass significance threshold max_pvalue (see clarification regarding this threshold below)

            - make a set union operation over all detected change points, so-called weak change points. They are "weak"
              change points because the algorithm uses modified (relaxed) max_pvalue for this step. In the current
              implementation the first-pass significance threshold is 10x of the original max_pvalue. For example, if we want
              to detect all change points at significance threshold 0.001, a threshold of 0.01 will be used at this step. Since
              it's a higher threshold for p-values, the algorithm will find more points. However, these points are just POTENTIAL
              change points, because some of them are significant at 0.01 but not at 0.001. In statistical terms, the evidence
              that they are change points is weak (only 0.01 compared to 0.001). Hence, the term "weak" change points. They will
              be filtered down to the final change points (with correct significance threshold) at the next step (Merge step)
              of the algorithm. For the reasoning on why change points cannot be computed right away (and the need for
              [weak change points -> change points] process) read Fleming et al. paper.

        2. Merge step:
            - Filters out weak change points recursively going bottom-up, keeping only high-quality change points, i.e., the
              ones that meet either a p-value threshold criteria or relative magnitude change criteria.
    """
    first_pass_pvalue = max_pvalue * 10 if max_pvalue < 0.05 else (max_pvalue * 2 if max_pvalue < 0.5 else max_pvalue)
    weak_change_points = split(series, window_len, first_pass_pvalue, new_points=new_data, old_cp=old_weak_cp)
    return merge(copy.copy(weak_change_points), series, max_pvalue, min_magnitude), weak_change_points
