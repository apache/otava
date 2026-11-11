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

import statistics

import numpy as np
import pytest

from otava.analysis import TTestSignificanceTester, compute_change_points
from otava.change_point_divisive.base import BaseStats
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector


@pytest.fixture(params=[(np.float16, 10000), (np.float32, 100000000)])
def low_precision_series(request):
    dtype, offset = request.param
    # Every residual is representable at either offset. Casting to float64
    # changes calculation precision without changing the observations.
    return dtype(offset) + np.array([0, 8, 16] * 3 + [-8, 0] * 7, dtype=dtype)


def test_statistics_use_accurate_means_and_sample_spreads(low_precision_series):
    left = low_precision_series[:9]
    right = low_precision_series[9:22]

    stats = BaseStats.calculate(left, right)

    # Python's statistics module is an independent, high-precision reference.
    left_values, right_values = list(map(float, left)), list(map(float, right))
    assert stats.mean_1 == pytest.approx(statistics.mean(left_values), rel=0, abs=1e-8)
    assert stats.mean_2 == pytest.approx(statistics.mean(right_values), rel=0, abs=1e-8)
    assert stats.std_1 == pytest.approx(statistics.stdev(left_values), rel=1e-12)
    assert stats.std_2 == pytest.approx(statistics.stdev(right_values), rel=1e-12)


def test_ttest_decision_is_invariant_to_represented_input_dtype(low_precision_series):
    tester = TTestSignificanceTester(0.001)
    values = low_precision_series
    reference = values.astype(np.float64)

    actual = tester.compare(values[:9], values[9:22])
    expected = tester.compare(reference[:9], reference[9:22])

    assert 0 < actual.pvalue < 0.001
    assert actual.pvalue == pytest.approx(expected.pvalue, rel=1e-12)
    assert actual.tstatistic == pytest.approx(expected.tstatistic, rel=1e-12)


def test_pair_distances_do_not_overflow_in_float16():
    values = np.array([-60000] * 3 + [60000] * 3, dtype=np.float16)

    with np.errstate(over='ignore', invalid='ignore'):
        candidate = PairDistanceCalculator(values).get_candidate_change_point(slice(None))

    assert candidate.index == 3
    # Nine cross-pairs at distance 120000, no within-group distances:
    # Q = 2 / (3 + 3) * 9 * 120000.
    assert candidate.qhat == pytest.approx(360000)


@pytest.mark.parametrize('algorithm', ['detector', 'split_merge'])
def test_detection_does_not_lose_boundary_with_lower_precision(low_precision_series, algorithm):
    values = low_precision_series
    original = values.copy()

    if algorithm == 'detector':
        detector = ChangePointDetector(TTestSignificanceTester(0.001), PairDistanceCalculator)
        points = detector.get_change_points(values)
    else:
        points, _ = compute_change_points(values, max_pvalue=0.001)

    assert [point.index for point in points] == [9]
    assert points[0].stats.mean_1 == pytest.approx(float(values[0]) + 8, rel=0, abs=1e-8)
    np.testing.assert_array_equal(values, original)


def test_pair_distances_preserve_exact_large_integer_differences():
    values = np.int64(2**60) + np.array([0, 1, 2, 10, 11, 12], dtype=np.int64)

    candidate = PairDistanceCalculator(values).get_candidate_change_point(slice(None))

    # Within-group pair sums are 4 each; the cross-group pair sum is 90.
    # Q = 2 / 6 * (90 - 3 / 2 * 4 - 3 / 2 * 4) = 26.
    assert candidate.index == 3
    assert candidate.qhat == pytest.approx(26)
