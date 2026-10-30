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

'''Tests for the windowed e-divisive computation (issue #84).

The window constraint lives inside `PairDistanceCalculator`: for a candidate
change point `tau` only the points within `window_len / 2` on either side take
part in the `Q` function. Three independent implementations are cross-checked:

    1. `_get_windowed_candidate` - the production O(N * window_len) scan;
    2. `_get_Q_vals_windowed`    - full (tau, kappa) matrix from block sums;
    3. `compute_windowed_Q_slow` - brute force straight from the QQ definition.
'''

import numpy as np
import pytest

from otava.analysis import TTestSignificanceTester, compute_change_points
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector


def compute_windowed_Q_slow(sequence, start, end, half):
    '''Brute-force windowed Q matrix, straight from the QQ definition.

    Q_w(tau, kappa) = QQ(series[max(start, tau - half) : tau], series[tau : kappa])
    for start < tau < kappa <= min(end, tau + half), -inf outside the band.
    '''
    size = end - start - 1
    Q = np.full((size, size), -np.inf)
    for tau in range(start + 1, end):
        left = max(start, tau - half)
        for kappa in range(tau + 1, min(end, tau + half) + 1):
            X, Y = sequence[left:tau], sequence[tau:kappa]
            n, m = len(X), len(Y)

            A = sum(abs(x - y) for x in X for y in Y) * 2 / (m + n)

            B = sum(abs(X[i] - X[k]) for i in range(n - 1) for k in range(i + 1, n))
            B *= 2 * m / (m + n) / (n - 1) if n > 1 else 0

            C = sum(abs(Y[j] - Y[k]) for j in range(m - 1) for k in range(j + 1, m))
            C *= 2 * n / (m + n) / (m - 1) if m > 1 else 0

            Q[tau - start - 1, kappa - start - 2] = A - B - C
    return Q


def assert_windowed_matches_brute_force(sequence, start, end, window_len):
    half = window_len // 2
    calc = PairDistanceCalculator(sequence, window_len=window_len)

    Q_matrix = calc._get_Q_vals_windowed(start, end)
    Q_brute = compute_windowed_Q_slow(sequence, start, end, half)
    band = np.isfinite(Q_brute)
    assert band.any(), "window band must not be empty"
    np.testing.assert_allclose(Q_matrix[band], Q_brute[band], atol=1e-8)
    assert np.all(~np.isfinite(Q_matrix[~band])), "matrix must be -inf outside the band"

    candidate = calc.get_candidate_change_point(slice(start, end))
    i, j = np.unravel_index(np.argmax(Q_brute), Q_brute.shape)
    assert candidate.index == i + 1 + start
    assert np.isclose(candidate.qhat, Q_brute[i, j], atol=1e-8)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
@pytest.mark.parametrize("window_len", [4, 6, 10, 16, 60])
def test_windowed_matches_brute_force(seed, window_len):
    rng = np.random.default_rng(seed)
    sequence = np.round(rng.normal(0, 1, 30), 3)
    sequence[15:20] += 4.0
    assert_windowed_matches_brute_force(sequence, 0, len(sequence), window_len)


def test_windowed_matches_brute_force_subinterval():
    # the detector evaluates candidates inside sub-intervals once the first
    # change point is accepted, so start > 0 must work as well
    rng = np.random.default_rng(42)
    sequence = np.round(rng.normal(0, 1, 50), 3)
    sequence[10:30] += 3.0
    sequence[35:] += 6.0
    for start, end in [(5, 45), (10, 40), (0, 25), (25, 50), (7, 49)]:
        for window_len in [6, 12, 30]:
            assert_windowed_matches_brute_force(sequence, start, end, window_len)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_large_window_is_equivalent_to_unwindowed(seed):
    # window_len >= 2 * len(series) must make the window constraint inactive:
    # exactly the same candidate and qhat as the unwindowed computation
    rng = np.random.default_rng(seed)
    sequence = np.round(rng.normal(0, 2, 40), 3)
    sequence[20:26] += 3.0
    sequence[33:] -= 2.0

    unwindowed = PairDistanceCalculator(sequence)
    candidate_unwindowed = unwindowed.get_candidate_change_point(slice(0, len(sequence)))

    for window_len in [2 * len(sequence), 10 * len(sequence)]:
        windowed = PairDistanceCalculator(sequence, window_len=window_len)
        candidate_windowed = windowed.get_candidate_change_point(slice(0, len(sequence)))
        assert candidate_windowed.index == candidate_unwindowed.index
        assert np.isclose(candidate_windowed.qhat, candidate_unwindowed.qhat)

    # and on the matrix level, for every (tau, kappa):
    Q_unwindowed = unwindowed._get_Q_vals(0, len(sequence))
    Q_windowed = PairDistanceCalculator(sequence, window_len=2 * len(sequence))._get_Q_vals_windowed(0, len(sequence))
    # compare the valid region only (kappa > tau); the unwindowed matrix leaves
    # zeros in the invalid lower triangle while the windowed one marks it -inf
    valid = np.triu(np.ones_like(Q_unwindowed, dtype=bool), k=0)
    np.testing.assert_allclose(Q_windowed[valid], Q_unwindowed[valid], atol=1e-8)


def test_windowed_candidate_two_close_change_points():
    # motivating case of issue #84: two change points that are closer to each
    # other than the window length. The windowed core must find both - and both
    # must dominate every spurious first-pass candidate by orders of magnitude
    # (the relaxed first-pass threshold may admit weak noise candidates; the
    # merge step filters those, exactly as in the Hunter design).
    sequence = np.concatenate([
        np.full(100, 10.0), np.full(40, 12.5), np.full(100, 10.0),
    ])
    rng = np.random.default_rng(11)
    sequence = sequence + rng.normal(0, 0.3, len(sequence))

    tester = TTestSignificanceTester(max_pvalue=0.01)
    detector = ChangePointDetector(
        significance_tester=tester,
        calculator=lambda series: PairDistanceCalculator(series, window_len=60),
    )
    change_points = detector.get_change_points(series=sequence)
    by_index = {cp.index: cp for cp in change_points}
    assert 100 in by_index and 140 in by_index
    assert by_index[100].stats.pvalue < 1e-10
    assert by_index[140].stats.pvalue < 1e-10
    assert all(cp.stats.pvalue > by_index[100].stats.pvalue
               for cp in change_points if cp.index not in (100, 140))


def test_windowed_core_end_to_end():
    # end-to-end: compute_change_points with core_window=True on a series with
    # three change points, two of which are closer than window_len to each other
    rng = np.random.default_rng(5)
    sequence = np.concatenate([
        np.full(150, 20.0),          # base level
        np.full(30, 22.0),           # regression 1 (short)
        np.full(150, 20.0),          # back to base
        np.full(120, 19.0),          # longer drift down
    ]) + rng.normal(0, 0.4, 450)

    change_points, weak = compute_change_points(
        sequence, window_len=60, max_pvalue=0.001, min_magnitude=0.0, core_window=True
    )
    indexes = [cp.index for cp in change_points]
    assert {150, 180, 330} <= set(indexes)
    # the first-pass (pre-merge) evidence for the true change points is overwhelming
    weak_by_index = {cp.index: cp for cp in weak}
    for true_idx in (150, 180, 330):
        assert weak_by_index[true_idx].stats.pvalue < 1e-10
    # and every merged change point is significant at the configured level
    assert all(cp.stats.pvalue <= 0.001 for cp in change_points)

    # the legacy chunked path on the same data (kept for A/B comparison).
    # Note: it must receive a list - the detector's start/end slicing only
    # applies to list input, ndarray input would detect over the whole series
    # and shift indexes (a latent trap that produces out-of-bounds change points).
    legacy_points, _ = compute_change_points(
        list(sequence), window_len=60, max_pvalue=0.001, min_magnitude=0.0, core_window=False
    )
    # both paths must at least agree on the big drift at 330
    assert 330 in [cp.index for cp in legacy_points]
