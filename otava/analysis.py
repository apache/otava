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
from dataclasses import dataclass
from typing import List, Optional, Sequence, SupportsFloat, Tuple

from scipy.stats import ttest_ind_from_stats

from otava.change_point_divisive.base import (
    BaseStats,
    CandidateChangePoint,
    ChangePoint,
    GenericStats,
    SignificanceTester,
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


# Generic Change Point List
GenCPList = List[ChangePoint[GenericStats]]
# Permutation Change Point List
PermCPList = List[ChangePoint[PermutationStats]]
# T-test Change Point List
TtestCPList = List[ChangePoint[TTestStats]]


# TODO: Move to change_point_divisive.significance_test
class TTestSignificanceTester(SignificanceTester):
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

    def change_point(
        self,
        candidate: CandidateChangePoint,
        series: Sequence[SupportsFloat],
        intervals: List[slice],
    ) -> ChangePoint[TTestStats]:
        left, right = self.get_sides(candidate, series, intervals)
        stats = self.compare(left, right)
        return ChangePoint.from_candidate(candidate, stats)


def fill_missing(data: Sequence[SupportsFloat]):
    """
    Forward-fills None occurrences with nearest previous non-None values.
    Initial None values are back-filled with the nearest future non-None value.

    TODO: Remove this.
    """
    prev = None
    for i in range(len(data)):
        if data[i] is None and prev is not None:
            data[i] = prev
        prev = data[i]

    prev = None
    for i in reversed(range(len(data))):
        if data[i] is None and prev is not None:
            data[i] = prev
        prev = data[i]


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

        # Remove the point from the list
        weakest_cp_index = change_points.index(weakest_cp)
        del change_points[weakest_cp_index]

        # We can't continue yet, because by removing a change_point
        # the adjacent change points changed their properties.
        # Recompute the adjacent change point stats:
        intervals = tester.get_intervals(change_points)

        def recompute(index: int):
            if index < 0 or index >= len(change_points):
                return
            cp = change_points[index]
            change_points[index] = tester.change_point(cp.to_candidate(), series, intervals)

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
        for cp in new_change_points:
            if cp not in change_points:
                change_points += [cp]

    # Sort change points by index; required by get_intervals() and maintained by merge()
    change_points.sort(key=lambda cp: cp.index)
    intervals = tester.get_intervals(change_points)
    return [tester.change_point(cp.to_candidate(), series, intervals) for cp in change_points]


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
