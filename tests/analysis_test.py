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
from scipy.stats import ttest_ind
from signal_processing_algorithms.e_divisive.change_points import EDivisiveChangePoint

from otava.analysis import TTestSignificanceTester, compute_change_points, fill_missing


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


def test_significance_tester():
    tester = TTestSignificanceTester(0.001)

    series = np.array([1.00, 1.02, 1.05, 0.95, 0.98, 1.00, 1.02, 1.05, 0.95, 0.98])
    cp = tester.change_point(5, series, [0, len(series)])
    assert not tester.is_significant(EDivisiveChangePoint(5), series, [0, len(series)])
    assert 0.99 < cp.stats.pvalue < 1.01

    series = np.array([1.00, 1.02, 1.05, 0.95, 0.98, 0.80, 0.82, 0.85, 0.79, 0.77])
    cp = tester.change_point(5, series, [0, len(series)])
    assert tester.is_significant(EDivisiveChangePoint(5), series, [0, len(series)])
    assert 0.00 < cp.stats.pvalue < 0.001


@pytest.mark.parametrize("tail, expected_indexes", [([], [4]), ([3.] * 4, [4, 12])])
def test_merge_refreshes_adjacent_statistics(tail, expected_indexes):
    # Removing boundary 8 joins the 2.0 and 2.05 segments. The surviving
    # boundaries must describe that combined segment, on both sides if present.
    values = [1.] * 4 + [2.] * 4 + [2.05] * 4 + tail

    points, _ = compute_change_points(
        values, window_len=50, max_pvalue=.001, min_magnitude=.1
    )

    assert [point.index for point in points] == expected_indexes
    np.testing.assert_allclose(points[0].stats.mean_2, 2.025)
    np.testing.assert_allclose(points[0].stats.std_2, .02672612419124244)
    if tail:
        np.testing.assert_allclose(points[1].stats.mean_1, 2.025)
        np.testing.assert_allclose(points[1].stats.std_1, .02672612419124244)


@pytest.mark.parametrize("left, right", [
    ([1., 2., 3.], [2., 4., 6.]),
    ([1.], [2., 3., 4.]),
    ([1., 2., 3.], [4.]),
    ([1., 1.], [2., 2.]),
    ([1.], [2.]),
])
def test_significance_uses_sample_standard_deviations(left, right):
    stats = TTestSignificanceTester(.05).compare(np.array(left), np.array(right))
    assert stats.std_1 == pytest.approx(np.std(left, ddof=1) if len(left) > 1 else 0.)
    assert stats.std_2 == pytest.approx(np.std(right, ddof=1) if len(right) > 1 else 0.)
    if len(left) + len(right) > 2:
        # SciPy 1.10 returns NaN for singleton raw samples; the pooled
        # Student t-test for these two fixtures has this finite p-value.
        expected = (.22540333075851657 if min(len(left), len(right)) == 1
                    else ttest_ind(left, right, equal_var=True).pvalue)
        assert stats.pvalue == pytest.approx(expected)
    else:
        assert stats.pvalue == 1.
