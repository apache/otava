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

from otava.analysis import (
    TTestSignificanceTester,
    compute_change_points,
    compute_change_points_orig,
)
from otava.change_point_divisive.base import BaseStats, Calculator, CandidateChangePoint
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector
from otava.change_point_divisive.significance_test import PermutationsSignificanceTester


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

    with np.errstate(over='raise', invalid='raise'):
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


@pytest.mark.parametrize('dtype', [np.float16, np.float32])
@pytest.mark.parametrize('group_size', [3, 25, 500])
@pytest.mark.parametrize('power', [1.0, 1.99])
def test_q_stays_finite_as_full_range_low_precision_series_grow(dtype, group_size, power):
    magnitude = float(np.finfo(dtype).max)
    values = np.array([-magnitude] * group_size + [magnitude] * group_size, dtype=dtype)
    calculator = PairDistanceCalculator(values, power=power)

    with np.errstate(over='raise', invalid='raise'):
        q_values = calculator._get_Q_vals(0, len(values))
        candidate = calculator.get_candidate_change_point(slice(None))

    # All within-group distances are zero. For k observations per side,
    # Q = 2 / (2k) * k**2 * distance = k * distance, so Q grows linearly.
    assert np.isfinite(q_values).all()
    assert np.isfinite(candidate.qhat)
    assert candidate.index == group_size
    assert candidate.qhat == pytest.approx(group_size * (2 * magnitude) ** power, rel=1e-12)


@pytest.mark.parametrize('values,power', [
    pytest.param([-1e308] * 3 + [1e308] * 3, 1.0, id='subtraction-overflow'),
    pytest.param([0.0] * 3 + [1e200] * 3, 1.99, id='power-overflow'),
    # The correct final Q is 2.5e307 and fits in float64, but intermediate
    # pair-distance sums exceed its range.
    pytest.param([0.0] * 25 + [1e306] * 25, 1.0, id='sum-overflow'),
    pytest.param([0.0, np.nan, 1.0], 1.0, id='nan-observation'),
    pytest.param([0.0, np.inf, 1.0], 1.0, id='infinite-observation'),
])
def test_calculator_rejects_unsupported_numeric_range(values, power):
    calculator = PairDistanceCalculator(np.array(values), power=power)

    # The calculator must enforce its contract even if callers ignore
    # NumPy overflow warnings.
    with np.errstate(over='ignore', invalid='ignore'):
        with pytest.raises(ValueError, match='rescale'):
            calculator.get_candidate_change_point(slice(None))


@pytest.mark.parametrize('algorithm', ['detector', 'split_merge', 'permutation'])
def test_detection_rejects_float64_intermediate_overflow(algorithm):
    values = np.array([0.0] * 25 + [1e306] * 25)

    with np.errstate(over='ignore', invalid='ignore'):
        with pytest.raises(ValueError, match='rescale'):
            if algorithm == 'detector':
                detector = ChangePointDetector(TTestSignificanceTester(0.001), PairDistanceCalculator)
                detector.get_change_points(values)
            elif algorithm == 'split_merge':
                compute_change_points(values)
            else:
                compute_change_points_orig(values, seed=1)


@pytest.mark.parametrize('qhat', [np.nan, np.inf, -np.inf])
def test_permutation_rejects_nonfinite_observed_score(qhat):
    values = np.array([0.0] * 3 + [1.0] * 3)
    candidate = CandidateChangePoint(index=3, qhat=qhat)
    tester = PermutationsSignificanceTester(0.05, 10, PairDistanceCalculator, seed=1)

    with pytest.raises(ValueError, match='finite'):
        tester.change_point(candidate, values, [slice(None)])


@pytest.mark.parametrize('qhat', [np.nan, np.inf, -np.inf])
def test_permutation_rejects_nonfinite_permuted_score(qhat):
    # Exercise the tester's calculator interface with an invalid score;
    # PairDistanceCalculator itself rejects these before returning a candidate.
    class NonfiniteScoreCalculator(Calculator):
        def get_candidate_change_point(self, interval):
            return CandidateChangePoint(index=3, qhat=qhat)

    values = np.array([0.0] * 3 + [1.0] * 3)
    candidate = CandidateChangePoint(index=3, qhat=3.0)
    tester = PermutationsSignificanceTester(0.05, 10, NonfiniteScoreCalculator, seed=1)

    with pytest.raises(ValueError, match='finite'):
        tester.change_point(candidate, values, [slice(None)])
