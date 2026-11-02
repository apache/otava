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

from otava.analysis import DeterministicTTestSignificanceTester, TTestSignificanceTester
from otava.change_point_divisive.calculator import PairDistanceCalculator
from otava.change_point_divisive.detector import ChangePointDetector
from otava.change_point_divisive.significance_test import PermutationsSignificanceTester


@pytest.mark.parametrize("method", ["ttest", "deterministic", "permutation"])
def test_two_point_interval_does_not_block_other_changes(method):
    # After splitting at 2, [0, 10] has Q=10 and cannot be split significantly.
    # The lower-Q change at 7 must still be discoverable in the other interval.
    series = np.array([
        0., 10., 100., 100.1, 99.9, 100.05, 99.95,
        101., 101.1, 100.9, 101.05, 100.95,
    ])
    if method == "permutation":
        tester = PermutationsSignificanceTester(0.05, 1000, PairDistanceCalculator, 1)
    elif method == "deterministic":
        tester = DeterministicTTestSignificanceTester(0.001)
    else:
        tester = TTestSignificanceTester(0.001)

    points = ChangePointDetector(tester, PairDistanceCalculator).get_change_points(series)

    assert [point.index for point in points] == [2, 7]
