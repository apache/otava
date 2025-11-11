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

from typing import List, Optional, Sequence, SupportsFloat, Type

import numpy as np

from otava.change_point_divisive.base import (
    Calculator,
    ChangePoint,
    GenericStats,
    SignificanceTester,
)


class ChangePointDetector:
    def __init__(self, significance_tester: SignificanceTester, calculator: Type[Calculator]):
        self.tester = significance_tester
        self.calculator = calculator

    def get_change_points(self, series: Sequence[SupportsFloat], start: Optional[int] = None, end: Optional[int] = None) -> List[ChangePoint[GenericStats]]:
        if not isinstance(series, np.ndarray):
            series = np.array(series[start : end], dtype=np.float64)
        if not np.issubdtype(series.dtype, np.floating):
            series = series.astype(np.float64, copy=False)

        calc = self.calculator(series)
        change_points = []

        while True:
            intervals = self.tester.get_intervals(change_points)
            candidate = calc.get_next_candidate(intervals)
            if candidate is None:
                break
            change_point = self.tester.change_point(candidate, series, intervals)
            if self.tester.is_significant(change_point):
                # TODO: Consider BST vs sorted array
                change_points.append(change_point)
                # Could sort by either start or end for non-intersecting intervals
                change_points.sort(key=lambda point: point.index)
            else:
                break

        if start is not None:
            for cp in change_points:
                cp.index += start

        return change_points
