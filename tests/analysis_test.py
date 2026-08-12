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
)
from otava.change_point_divisive.base import CandidateChangePoint


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

    # incremental change point detection:
    cps, _ = compute_change_points(series, max_pvalue=0.0001, new_data=0.47, old_weak_cp=cps)
    indexes = [c.index for c in cps]
    assert indexes == [10]

    # decrease window_len to generate more cp and hit the last two lines in code cov...
    cps, _ = compute_change_points(series+[0.47, 0.48, 0.45, 0.01, 0.1, 0.22], max_pvalue=0.0001, new_data=0.27, old_weak_cp=cps, window_len=5)
    indexes = [c.index for c in cps]
    assert indexes == [10, 23]

    cps = [cps[0]]
    cps[0].index = 2
    cps, _ = compute_change_points(series+[0.47, 0.48, 0.45, 0.01, 0.1, 0.22], max_pvalue=0.0001, new_data=0.27, old_weak_cp=cps, window_len=5)
    indexes = [c.index for c in cps]
    assert indexes == [10, 23]


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
