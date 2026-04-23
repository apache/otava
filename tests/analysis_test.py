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

from otava.analysis import (
    TTestSignificanceTester,
    compute_change_points,
    compute_change_points_orig,
    fill_missing,
)
from otava.change_point_divisive.base import CandidateChangePoint


def test_fill_missing():
    list1 = [None, None, 1.0, 1.2, 0.5]
    list2 = [1.0, 1.2, None, None, 4.3]
    list3 = [1.0, 1.2, 0.5, None, None]
    fill_missing(list1)
    fill_missing(list2)
    fill_missing(list3)
    assert list1 == [1.0, 1.0, 1.0, 1.2, 0.5]
    assert list2 == [1.0, 1.2, 1.2, 1.2, 4.3]
    assert list3 == [1.0, 1.2, 0.5, 0.5, 0.5]


def test_single_series():
    series = [
        1.02,
        0.95,
        0.99,
        1.00,
        1.12,
        1.00,
        1.01,
        0.98,
        1.01,
        0.96,
        0.50,
        0.51,
        0.48,
        0.48,
        0.55,
        0.50,
        0.49,
        0.51,
        0.50,
        0.49,
    ]
    cps, _ = compute_change_points(series, window_len=10, max_pvalue=0.0001)
    indexes = [c.index for c in cps]
    assert indexes == [10]


def test_single_series_original():
    series = [
        1.02,
        0.95,
        0.99,
        1.00,
        1.12,
        1.00,
        1.01,
        0.98,
        1.01,
        0.96,
        0.50,
        0.51,
        0.48,
        0.48,
        0.55,
        0.50,
        0.49,
        0.51,
        0.50,
        0.49,
    ]
    cps, _ = compute_change_points_orig(series, max_pvalue=0.0001, seed=1)
    indexes = [c.index for c in cps]
    assert indexes == [10]


def test_significance_tester():
    tester = TTestSignificanceTester(0.001)

    series = np.array([1.00, 1.02, 1.05, 0.95, 0.98, 1.00, 1.02, 1.05, 0.95, 0.98])
    candidate = CandidateChangePoint(index=5, qhat=0.)
    cp = tester.change_point(candidate, series, intervals=[slice(None, None)])
    assert not tester.is_significant(cp)
    assert 0.99 < cp.stats.pvalue < 1.01

    series = np.array([1.00, 1.02, 1.05, 0.95, 0.98, 0.80, 0.82, 0.85, 0.79, 0.77])
    candidate = CandidateChangePoint(index=5, qhat=0.)
    cp = tester.change_point(candidate, series, intervals=[slice(None, None)])
    assert tester.is_significant(cp)
    assert 0.00 < cp.stats.pvalue < 0.001


def test_single_point_spike_is_removed_by_min_segment_len():
    series = [100, 100, 100, 100, 300, 100, 100, 100, 100]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == []


def test_clean_step_is_preserved_by_min_segment_len():
    series = [100, 100, 100, 100, 110, 110, 110, 110, 110]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == [4]


def test_spike_then_shift_collapses_to_real_change_point():
    series = [100, 100, 100, 100, 300, 110, 110, 110, 110]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == [5]


def test_later_step_after_short_regime_is_ignored_when_segment_too_short():
    series = [100, 100, 100, 100, 300, 100, 100, 110, 110]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == []


def test_short_regime_is_ignored_when_shorter_than_min_segment_len():
    series = [100, 100, 100, 100, 300, 300, 100, 100, 100]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == []


def test_multiple_sustained_steps_are_preserved_by_min_segment_len():
    series = [100, 100, 100, 100, 130, 130, 130, 130, 150, 150, 150, 150]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == [4, 8]


def test_two_point_middle_regime_is_suppressed_by_min_segment_len():
    series = [100, 100, 100, 100, 130, 130, 150, 150, 150, 150]

    cps, _ = compute_change_points(
        series,
        window_len=5,
        max_pvalue=0.001,
        min_magnitude=0.01,
        min_segment_len=3,
    )

    assert [cp.index for cp in cps] == [6]
