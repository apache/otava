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

import math

import numpy as np
import pytest
from scipy.stats import ttest_ind

from otava.analysis import TTestSignificanceTester
from otava.change_point_divisive.base import BaseStats, ChangePoint


def test_ttest_uses_sample_variance_for_significance():
    tester = TTestSignificanceTester(0.05)

    stats = tester.compare([0, 1], [3, 4])

    # Pooled within-sample sum of squares is 1, with two degrees of freedom.
    assert stats.tstatistic == pytest.approx(-4.242640687119285)
    assert stats.pvalue == pytest.approx(0.05131670194948621)
    assert stats.degrees_of_freedom == 2
    assert not tester.is_significant(ChangePoint(index=2, qhat=0, stats=stats))


@pytest.mark.filterwarnings("ignore:Precision loss occurred in moment calculation:RuntimeWarning")
@pytest.mark.parametrize("left, right", [
    ([0, 1], [3, 4]),
    ([1, 2, 5], [0, 4, 6]),
    ([1, 4], [2, 3, 6, 8, 12]),
    ([2], [1, 3, 6, 8]),
    ([1, 3, 6, 8], [2]),
    ([2, 2], [1, 3, 6]),
    ([2, 2], [3, 3, 3]),
])
def test_ttest_matches_raw_sample_student_test(left, right):
    # This independent oracle computes variance from raw data, not BaseStats.
    expected = ttest_ind(left, right, equal_var=True, alternative="two-sided")

    actual = TTestSignificanceTester(0.05).compare(left, right)

    assert actual.tstatistic == pytest.approx(expected.statistic)
    assert actual.pvalue == pytest.approx(expected.pvalue)
    assert actual.degrees_of_freedom == expected.df


def test_ttest_matches_raw_sample_student_test_for_seeded_samples():
    rng = np.random.default_rng(20261108)
    tester = TTestSignificanceTester(0.05)
    for _ in range(500):
        n_left, n_right = rng.integers(1, 31, size=2)
        if n_left + n_right == 2:
            n_right = 2
        left = rng.normal(rng.uniform(-10, 10), rng.uniform(0.1, 5), n_left)
        right = rng.normal(rng.uniform(-10, 10), rng.uniform(0.1, 5), n_right)
        expected = ttest_ind(left, right, equal_var=True, alternative="two-sided")

        actual = tester.compare(left, right)

        assert actual.tstatistic == pytest.approx(expected.statistic, rel=1e-12)
        assert actual.pvalue == pytest.approx(expected.pvalue, rel=1e-12)
        assert actual.degrees_of_freedom == expected.df


def test_ttest_keeps_population_descriptive_statistics():
    left, right = [0, 2], [4, 8, 12]
    base = BaseStats.calculate(left, right)

    stats = TTestSignificanceTester(0.05).compare(left, right)

    expected = (1.0, 8.0, 1.0, math.sqrt(32 / 3))
    assert (base.mean_1, base.mean_2, base.std_1, base.std_2) == pytest.approx(expected)
    assert (stats.mean_1, stats.mean_2, stats.std_1, stats.std_2) == pytest.approx(expected)
    serialized = stats.to_json()
    assert serialized["mean_before"] == "1.000000"
    assert serialized["mean_after"] == "8.000000"
    assert serialized["stddev_before"] == "1.000000"
    assert serialized["stddev_after"] == "3.265986"
    point = ChangePoint(index=2, qhat=0, stats=stats).to_json()
    assert (point["mean_before"], point["mean_after"],
            point["stddev_before"], point["stddev_after"]) == pytest.approx(expected)


@pytest.mark.parametrize("left, right", [([1], [1]), ([1], [2])])
def test_ttest_two_singletons_keep_zero_df_fallback(left, right):
    stats = TTestSignificanceTester(0.05).compare(left, right)

    assert stats.pvalue == 1.0
    assert stats.tstatistic == 0.0
    assert stats.degrees_of_freedom == 0
    assert stats.std_1 == stats.std_2 == 0.0


def test_ttest_identical_constant_samples_keep_undefined_result():
    stats = TTestSignificanceTester(0.05).compare([2, 2], [2, 2, 2])

    assert math.isnan(stats.tstatistic)
    assert math.isnan(stats.pvalue)


@pytest.mark.parametrize("left, right", [([], [1]), ([1], []), ([], [])])
def test_ttest_rejects_empty_samples(left, right):
    with pytest.raises(ValueError):
        TTestSignificanceTester(0.05).compare(left, right)
