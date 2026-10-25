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

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from scipy.stats import t as student_t

from otava.analysis import compute_change_points_deterministic
from otava.series import AnalysisOptions, Metric, Series
from tests.tigerbeetle_test import tigerbeetle_demo_data


def adjacent_statistics(values, indexes):
    """Calculate expected statistics directly from specified segment boundaries."""
    bounds = [0] + indexes + [len(values)]
    result = []
    for i in range(len(indexes)):
        left = values[bounds[i]:bounds[i + 1]]
        right = values[bounds[i + 1]:bounds[i + 2]]
        n, m = len(left), len(right)
        a, b = np.mean(left), np.mean(right)
        std_1, std_2 = np.std(left), np.std(right)
        df = n + m - 2
        statistic, pvalue = 0., 1.
        if df > 0:
            variance = ((n - 1) * std_1 ** 2 + (m - 1) * std_2 ** 2) / df
            with np.errstate(divide="ignore", invalid="ignore"):
                statistic = np.divide(a - b, np.sqrt(variance * (1 / n + 1 / m)))
            pvalue = 2 * student_t.sf(abs(statistic), df)
        magnitude = max(abs(b / a - 1) if a else 0., abs(a / b - 1) if b else 0.)
        result.append({
            "mean_1": a, "mean_2": b, "std_1": std_1, "std_2": std_2,
            "pvalue": pvalue, "tstatistic": statistic,
            "degrees_of_freedom": df, "magnitude": magnitude,
        })
    return result


def assert_adjacent_statistics(points, values, indexes):
    assert [point.index for point in points] == indexes
    for point, expected in zip(points, adjacent_statistics(values, indexes)):
        for name, value in expected.items():
            actual = point.stats.change_magnitude() if name == "magnitude" else getattr(point.stats, name)
            np.testing.assert_allclose(actual, value, rtol=1e-12, atol=1e-12)


@pytest.mark.parametrize("min_magnitude", [-1., 0.])
@pytest.mark.parametrize("as_array", [False, True])
def test_statistics_describe_adjacent_segments_after_all_splits(min_magnitude, as_array):
    """Report each 1 -> 5 -> 9 boundary against its immediate neighboring segments."""
    values = [1.] * 20 + [5.] * 20 + [9.] * 12
    if as_array:
        values = np.array(values)

    points, unfiltered = compute_change_points_deterministic(values, min_magnitude=min_magnitude)

    assert_adjacent_statistics(points, values, [20, 40])
    assert_adjacent_statistics(unfiltered, values, [20, 40])


@pytest.mark.parametrize("number_type", [Decimal, Fraction])
@pytest.mark.parametrize("as_array", [False, True])
@pytest.mark.parametrize("threshold,indexes", [(0., [10, 20, 30]), (.18, [10, 30])])
def test_statistics_accept_float_convertible_values(number_type, as_array, threshold, indexes):
    """Use float-convertible inputs for discovery and all subsequent comparisons."""
    numeric = [8] * 10 + [9] * 10 + [10] * 10 + [20] * 10
    values = [number_type(value) for value in numeric]
    if as_array:
        values = np.array(values, dtype=object)

    points, unfiltered = compute_change_points_deterministic(values, min_magnitude=threshold)

    assert_adjacent_statistics(points, numeric, indexes)
    assert_adjacent_statistics(unfiltered, numeric, [10, 20, 30])
    assert all(isinstance(value, number_type) for value in values)


@pytest.mark.parametrize("levels,threshold,expected_indexes", [
    ([8., 9., 10., 20.], .18, [10, 30]),
    ([10., 11., 13.], .2, [20]),
    ([10., 12., 10.5, 20.], .15, [30]),
    ([10., 9.1, 11.], .18, []),
], ids=["predecessor-retained", "successor-retained", "predecessor-removed", "successor-removed"])
def test_magnitude_filter_refreshes_neighbors_before_next_removal(levels, threshold, expected_indexes):
    """Removing a boundary may move either neighbor above or below the cutoff.

    Use ten samples per level; check the retained boundaries and final statistics.
    """
    values = [value for level in levels for value in [level] * 10]

    points, unfiltered = compute_change_points_deterministic(values, min_magnitude=threshold)

    assert_adjacent_statistics(points, values, expected_indexes)
    assert all(point.stats.change_magnitude() >= threshold for point in points)
    assert_adjacent_statistics(unfiltered, values, list(range(10, len(values), 10)))


@pytest.mark.parametrize("threshold,expected_indexes", [(.25, [10]), (.25001, [])])
def test_magnitude_filter_includes_boundary_equal_to_threshold(threshold, expected_indexes):
    """Keep the 8 -> 10 change at a 25% cutoff and remove it above that cutoff."""
    values = [8.] * 10 + [10.] * 10

    points, unfiltered = compute_change_points_deterministic(values, min_magnitude=threshold)

    assert_adjacent_statistics(points, values, expected_indexes)
    assert_adjacent_statistics(unfiltered, values, [10])


@pytest.mark.parametrize("values", [[], [1.], [1.] * 20])
@pytest.mark.parametrize("threshold", [0., .1])
def test_final_statistics_allow_series_without_change_points(values, threshold):
    """Empty, singleton, and constant histories return no points at either cutoff."""
    points, unfiltered = compute_change_points_deterministic(values, min_magnitude=threshold)

    assert points == []
    assert unfiltered == []


def test_tigerbeetle_magnitudes_and_statistics_match_retained_segments():
    """Apply the 3% cutoff to current neighbors until all retained points qualify."""
    values = tigerbeetle_demo_data()

    points, unfiltered = compute_change_points_deterministic(values, max_pvalue=.2, min_magnitude=.03)

    assert_adjacent_statistics(points, values, [10, 11, 15, 61, 71, 95, 131, 192, 363])
    assert all(point.stats.change_magnitude() >= .03 for point in points)
    assert_adjacent_statistics(unfiltered, values, [10, 11, 15, 61, 71, 95, 117, 131, 142, 148, 192, 212, 260, 363])


def test_discovery_significance_is_distinct_from_final_segment_pvalue():
    """Keep kappa-selected boundaries while reporting p-values for final segments."""
    values = tigerbeetle_demo_data()

    points, _ = compute_change_points_deterministic(values, max_pvalue=1e-5)

    assert_adjacent_statistics(points, values, [10, 15, 71, 95, 131, 192])
    assert points[0].stats.pvalue == pytest.approx(.12874352438042228)


def test_serialized_statistics_describe_filtered_segments():
    """Persist means, deviations, p-values, and magnitudes for the retained boundaries."""
    values = [8.] * 10 + [9.] * 10 + [10.] * 10 + [20.] * 10
    options = AnalysisOptions(deterministic_edivisive=True, split_edivisive=False, min_magnitude=.18)
    analyzed = Series(
        "statistics", branch=None, time=list(range(len(values))),
        metrics={"latency": Metric()}, data={"latency": values}, attributes={},
    ).analyze(options)

    payload = analyzed.to_json()

    groups = payload["change_points"]["latency"]
    assert [group["time"] for group in groups] == [10, 30]
    names = {"mean_before": "mean_1", "mean_after": "mean_2", "stddev_before": "std_1", "stddev_after": "std_2", "pvalue": "pvalue", "magnitude": "magnitude"}
    for group, expected in zip(groups, adjacent_statistics(values, [10, 30])):
        stored = group["changes"][0]
        for key, name in names.items():
            assert stored[key] == pytest.approx(expected[name])
