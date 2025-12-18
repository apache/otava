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

import numpy as np
import pytest

from otava.analysis import TTestSignificanceTester, TTestStats
from otava.change_point_divisive.base import ChangePoint
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector
from otava.change_point_divisive.significance_test import PermutationsSignificanceTester

SEQUENCE = np.array([
    0.3, 2.4, 1.5, -0.9, -0.5,
    99.7, 98.3, 99.1,
    149.0, 149.7, 149.5, 149.1, 148.8, 150.0,
])
CHANGE_POINTS_INDS = [5, 8]


def compute_Q_and_candidate_slow(sequence):
    N = len(sequence)
    Q = np.zeros((N - 1, N - 1))
    Q_max = 0
    candidate_ind = None
    for tau in range(1, N):
        for kappa in range(tau + 1, N + 1):
            X, Y = sequence[: tau], sequence[tau : kappa]
            n, m = len(X), len(Y)

            A = 0
            for x in X:
                for y in Y:
                    A += abs(x - y)
            A *= 2 / (m + n)

            B = 0
            for i in range(n - 1):
                for k in range(i + 1, n):
                    B += abs(X[i] - X[k])
            B *= 2 * m / (m + n) / (n - 1) if n > 1 else 0

            C = 0
            for j in range(m - 1):
                for k in range(j, m):
                    C += abs(Y[j] - Y[k])
            C *= 2 * n / (m + n) / (m - 1) if m > 1 else 0

            Q[tau - 1, kappa - 2] = A - B - C
            if Q[tau - 1, kappa - 2] > Q_max:
                Q_max = Q[tau - 1, kappa - 2]
                candidate_ind = tau

    return Q, Q_max, candidate_ind


def test_calculator_candidate():
    sequence = SEQUENCE.copy()
    calc = PairDistanceCalculator(sequence)
    Q = calc._get_Q_vals(start=0, end=len(sequence))

    test_Q, test_Q_max, test_candidate_ind = compute_Q_and_candidate_slow(sequence)
    assert np.allclose(test_Q, Q)

    whole_interval = slice(None, None)
    candidate = calc.get_candidate_change_point(whole_interval)
    assert np.allclose(test_Q_max, candidate.qhat)
    assert test_candidate_ind == candidate.index


def test_permutation_calculation():
    sequence = SEQUENCE.copy()
    calc = PairDistanceCalculator(sequence)
    whole_interval = slice(None, None)
    candidate = calc.get_candidate_change_point(whole_interval)

    seed = 1
    st = PermutationsSignificanceTester(max_pvalue=0.05, permutations=1, calculator=PairDistanceCalculator, seed=seed)
    change_point = st.change_point(candidate=candidate, series=sequence, intervals=[whole_interval])

    test_rng = np.random.default_rng(seed)
    rand_sequence = sequence.copy()
    test_rng.shuffle(rand_sequence)
    _, rand_Q_max, rand_candidate_ind = compute_Q_and_candidate_slow(rand_sequence)
    assert int(rand_Q_max >= candidate.qhat) == change_point.stats.extreme_qhat_perm
    assert np.allclose(rand_Q_max, change_point.stats.permuted_qhats[0])


def test_permutation_test():
    seed = 1
    sequence = SEQUENCE.copy()
    st = PermutationsSignificanceTester(max_pvalue=0.01, permutations=100, calculator=PairDistanceCalculator, seed=seed)
    cpd = ChangePointDetector(significance_tester=st, calculator=PairDistanceCalculator)
    cps = cpd.get_change_points(series=sequence)
    assert [cp.index for cp in cps] == CHANGE_POINTS_INDS


def test_ttest():
    sequence = SEQUENCE.copy()
    st = TTestSignificanceTester(max_pvalue=0.01)
    cpd = ChangePointDetector(significance_tester=st, calculator=PairDistanceCalculator)
    cps = cpd.get_change_points(series=sequence)
    assert [cp.index for cp in cps] == CHANGE_POINTS_INDS


def test_get_intervals_requires_sorted_change_points():
    """Test that get_intervals() raises AssertionError when change points are not sorted by index."""
    tester = TTestSignificanceTester(max_pvalue=0.01)
    stats = TTestStats(mean_1=1.0, mean_2=2.0, std_1=0.1, std_2=0.1, pvalue=0.001)

    # Sorted change points should work
    sorted_cps = [
        ChangePoint(index=5, qhat=1.0, stats=stats),
        ChangePoint(index=10, qhat=1.0, stats=stats),
        ChangePoint(index=15, qhat=1.0, stats=stats),
    ]
    intervals = tester.get_intervals(sorted_cps)
    assert len(intervals) == 4
    assert intervals[0] == slice(0, 5)
    assert intervals[1] == slice(5, 10)
    assert intervals[2] == slice(10, 15)
    assert intervals[3] == slice(15, None)

    # Unsorted change points should raise AssertionError
    unsorted_cps = [
        ChangePoint(index=10, qhat=1.0, stats=stats),
        ChangePoint(index=5, qhat=1.0, stats=stats),
        ChangePoint(index=15, qhat=1.0, stats=stats),
    ]
    with pytest.raises(AssertionError, match="Change points must be sorted by index"):
        tester.get_intervals(unsorted_cps)
