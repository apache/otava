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

from dataclasses import dataclass, fields
from typing import Generic, List, Optional, TypeVar

from numpy.typing import NDArray


@dataclass
class CandidateChangePoint:
    '''Candidate for a change point. The point that maximizes Q-hat function on [start:end+1] slice'''
    index: int
    qhat: float


@dataclass
class BaseStats:
    '''Abstract statistics class for change point. Implementation depends on the statistical test.'''
    pvalue: float


GenericStats = TypeVar("GenericStats", bound=BaseStats)


@dataclass
class ChangePoint(CandidateChangePoint, Generic[GenericStats]):
    '''Change point class, defined by index and signigicance test statistic.'''
    stats: GenericStats

    def __eq__(self, other):
        '''Helpful to identify new Change Points during divisive algorithm'''
        return isinstance(other, self.__class__) and self.index == other.index

    @classmethod
    def from_candidate(cls, candidate: CandidateChangePoint, stats: GenericStats) -> 'ChangePoint[GenericStats]':
        return cls(
            index=candidate.index,
            qhat=candidate.qhat,
            stats=stats,
        )

    def to_candidate(self) -> CandidateChangePoint:
        '''Downgrades Change Point to a Candidate Change Point. Used to recompute stats for Weak Change Points.'''
        data = {f.name: getattr(self, f.name) for f in fields(CandidateChangePoint)}
        return CandidateChangePoint(**data)


class SignificanceTester(Generic[GenericStats]):
    '''Abstract class for significance tester'''

    def __init__(self, alpha: float):
        self.alpha = alpha

    def get_intervals(self, change_points: List[ChangePoint[GenericStats]]) -> List[slice]:
        '''Returns list of slices of the series'''
        intervals = [
            slice(
                0 if i == 0 else change_points[i - 1].index,
                None if i == len(change_points) else change_points[i].index,
            )
            for i in range(len(change_points) + 1)
        ]
        return [interval for interval in intervals if interval.start != interval.stop]

    def is_significant(self, point: ChangePoint[GenericStats]) -> bool:
        '''Compares ChangePoint to level of significance alpha'''
        return point.stats.pvalue <= self.alpha

    def change_point(self, candidate: CandidateChangePoint, series: NDArray, intervals: List[slice]) -> ChangePoint[GenericStats]:
        '''Computes stats for a change point candidate and wraps it into ChangePoint class'''
        ...


class Calculator:
    '''Abstract class for calculator. Calculator provides an interface to get best change point candidate'''
    def __init__(self, series: NDArray):
        self.series = series

    def get_next_candidate(self, intervals: List[slice]) -> Optional[CandidateChangePoint]:
        '''Returns list of existing change points to find next best change point candidate.'''
        candidates = [
            self.get_candidate_change_point(interval=interval)
            for interval in intervals
            if len(self.series[interval]) > 1
        ]
        if not candidates:
            return
        candidate = max(candidates, key=lambda point: point.qhat)
        return candidate

    def get_candidate_change_point(self, interval: slice) -> CandidateChangePoint:
        '''Given start and end indexes return best candidate for a change point.
        Note that start and end are indexes of the first and last element, i.e. a slice [start:end+1].'''
        ...
