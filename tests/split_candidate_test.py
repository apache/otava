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

from otava import analysis
from otava.analysis import TTestSignificanceTester
from otava.change_point_divisive import base
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector
from otava.change_point_divisive.significance_test import PermutationsSignificanceTester
from tests.change_point_divisive_test import SEQUENCE


@pytest.mark.parametrize("start", [0, 7])
def test_calculator_preserves_winning_endpoint(start):
    sequence = np.array([-10.] * start + [1.] * 50 + [2.] * 5 + [1.] * 100)
    candidate = PairDistanceCalculator(sequence).get_candidate_change_point(slice(start, None))

    assert candidate.index == start + 50
    assert candidate.kappa == start + 55
    assert candidate.qhat == pytest.approx(100 / 11)


@pytest.mark.parametrize("kappa", [4, 5])
def test_split_candidate_rejects_empty_or_reversed_right_sample(kappa):
    with pytest.raises(ValueError, match="kappa"):
        base.SplitCandidate(index=5, kappa=kappa, qhat=1.)


def test_split_candidate_requires_endpoint():
    with pytest.raises(TypeError, match="kappa"):
        base.SplitCandidate(index=5, qhat=1.)


@pytest.mark.parametrize("tester_name", ["TTestSignificanceTester", "DeterministicTTestSignificanceTester"])
@pytest.mark.parametrize("serialized", [False, True])
def test_recompute_uses_current_neighbors_and_preserves_metric(tester_name, serialized):
    tester = getattr(analysis, tester_name)(0.001)
    old_stats = tester.compare([1., 1.], [10., 10.])
    point = base.ChangePoint(index=4, qhat=12., stats=old_stats, metric="latency")
    if serialized:
        point = base.ChangePointSerializer(point)
    sequence = [-100., -100., 1., 3., 5., 7., 9., 100.]

    updated = tester.recompute_change_point(
        point, sequence, [slice(0, 2), slice(2, 4), slice(4, 7), slice(7, None)]
    )

    assert (updated.index, updated.qhat, updated.metric) == (4, 12., "latency")
    assert updated.stats.mean_1 == 2.
    assert updated.stats.std_1 == 1.
    assert updated.stats.mean_2 == 7.
    assert updated.stats.std_2 == pytest.approx(np.sqrt(8 / 3))
    assert updated.stats.degrees_of_freedom == 3
    assert point.stats is old_stats
    assert point.stats.mean_2 == 10.


@pytest.mark.parametrize("as_array", [False, True])
@pytest.mark.parametrize("start,end", [(7, 21), (-21, -7)])
def test_detector_limits_analysis_to_requested_window(as_array, start, end):
    sequence = [500.] * 7 + list(SEQUENCE) + [-500.] * 7
    if as_array:
        sequence = np.array(sequence)
    detector = ChangePointDetector(TTestSignificanceTester(0.01), PairDistanceCalculator)

    points = detector.get_change_points(sequence, start=start, end=end)

    assert [point.index for point in points] == [12, 15]
    assert points[0].stats.mean_1 == pytest.approx(0.56)
    assert points[1].stats.mean_2 == pytest.approx(149.35)


def test_deterministic_detects_short_regression_and_recovery():
    points, _ = analysis.compute_change_points_deterministic([1.] * 50 + [2.] * 5 + [1.] * 100)

    assert [point.index for point in points] == [50, 55]
    assert points[0].stats.mean_1 == 1.
    assert points[0].stats.mean_2 == 2.
    assert points[0].stats.degrees_of_freedom == 53
    assert points[1].stats.mean_1 == 2.
    assert points[1].stats.mean_2 == 1.


@pytest.mark.parametrize("qhat", [0., 1e8])
@pytest.mark.parametrize("kappa,mean_2,std_2,df", [(6, 6., 1., 2), (8, 8., np.sqrt(5), 4)])
def test_deterministic_uses_containing_interval_start_and_exclusive_endpoint(kappa, mean_2, std_2, df, qhat):
    tester = analysis.DeterministicTTestSignificanceTester(0.001)
    sequence = [-100., -100., 1., 3., 5., 7., 9., 11., 100., 100.]
    candidate = base.SplitCandidate(index=4, kappa=kappa, qhat=qhat)

    point = tester.evaluate_candidate(candidate, sequence, [slice(0, 2), slice(2, 8), slice(8, None)])

    assert point.index == 4
    assert point.qhat == qhat
    assert point.stats.mean_1 == 2.
    assert point.stats.std_1 == 1.
    assert point.stats.mean_2 == mean_2
    assert point.stats.std_2 == pytest.approx(std_2)
    assert point.stats.degrees_of_freedom == df
    if kappa == 6:
        assert point.stats.tstatistic == -4.
        assert point.stats.pvalue == pytest.approx(0.05719095841793663)


@pytest.mark.parametrize("index,kappa", [(4, 9), (4, 11), (2, 6), (-1, 1), (9, 11), (10, 11)])
def test_deterministic_rejects_candidate_outside_containing_interval(index, kappa):
    tester = analysis.DeterministicTTestSignificanceTester(0.001)
    candidate = base.SplitCandidate(index=index, kappa=kappa, qhat=1.)

    with pytest.raises(ValueError):
        tester.evaluate_candidate(candidate, list(range(10)), [slice(0, 2), slice(2, 8), slice(8, None)])


@pytest.mark.parametrize("as_array", [False, True])
def test_deterministic_window_preserves_both_sample_coordinates(as_array):
    sequence = [-100.] * 7 + [1.] * 50 + [2.] * 5 + [1.] * 100 + [-100.] * 7
    if as_array:
        sequence = np.array(sequence)
    tester = analysis.DeterministicTTestSignificanceTester(0.001)
    detector = ChangePointDetector(tester, PairDistanceCalculator)

    points = detector.get_change_points(sequence, start=7, end=162)

    assert [point.index for point in points] == [57, 62]
    assert points[0].stats.mean_1 == 1.
    assert points[0].stats.mean_2 == 2.
    assert points[0].stats.degrees_of_freedom == 53


@pytest.mark.parametrize("kappa", [6, len(SEQUENCE)])
def test_hunter_keeps_interval_endpoint(kappa):
    tester = TTestSignificanceTester(0.001)
    candidate = base.SplitCandidate(index=5, kappa=kappa, qhat=761.2821428571428)

    point = tester.evaluate_candidate(candidate, SEQUENCE, [slice(None, None)])

    assert point.stats.mean_1 == pytest.approx(0.56)
    assert point.stats.mean_2 == pytest.approx(132.57777777777775)
    assert point.stats.degrees_of_freedom == 12


@pytest.mark.parametrize("kappa", [6, len(SEQUENCE)])
def test_permutation_significance_uses_score_independently_of_endpoint(kappa):
    tester = PermutationsSignificanceTester(0.01, 100, PairDistanceCalculator, seed=1)
    candidate = base.SplitCandidate(index=5, kappa=kappa, qhat=761.2821428571428)

    point = tester.evaluate_candidate(candidate, SEQUENCE, [slice(None, None)])

    assert point.stats.pvalue == 0.
    assert point.stats.extreme_qhat_perm == 0
    assert point.stats.mean_2 == pytest.approx(132.57777777777775)
