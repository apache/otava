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

from dataclasses import dataclass
from typing import List, Optional, Type

import numpy as np
from numpy.typing import NDArray

from otava.change_point_divisive.base import (
    BaseStats,
    Calculator,
    CandidateChangePoint,
    ChangePoint,
    SignificanceTester,
)


@dataclass
class PermutationStats(BaseStats):
    '''Statistics for permutation significance test'''
    permuted_qhats: NDArray
    extreme_qhat_perm: int
    n_perm: int


class PermutationsSignificanceTester(SignificanceTester):
    def __init__(self, alpha: float, permurations: int, calculator: Type[Calculator], seed: Optional[int]):
        '''alpha - significance level
        permutations - number of permutations to run to test significance
        calculator - Calculator class to perform permutations (and compute new qhat value)
        '''
        super().__init__(alpha)
        self.permutations = permurations
        self.calculator = calculator
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def change_point(self, candidate: CandidateChangePoint, series: NDArray, intervals: List[slice]) -> ChangePoint[PermutationStats]:
        '''Perform permutation test within candidate cluster'''

        # 1. Find permutated Qhats
        qhats = np.empty(self.permutations)
        for i in range(self.permutations):
            # Permute points within each interval (cluster)
            rand_series = series.copy()
            for interval in intervals:
                seg = rand_series[interval]
                self.rng.shuffle(seg)
            rand_calc = self.calculator(rand_series)
            rand_candidate = rand_calc.get_next_candidate(intervals)
            qhats[i] = rand_candidate.qhat

        # 2. Estimate p-value
        extreme_qhat_perm = np.sum(qhats >= candidate.qhat)
        pval = extreme_qhat_perm / (self.permutations + 1)
        stats = PermutationStats(
            pvalue=pval,
            permuted_qhats=qhats,
            extreme_qhat_perm=extreme_qhat_perm,
            n_perm=self.permutations
        )
        return ChangePoint.from_candidate(candidate, stats)
