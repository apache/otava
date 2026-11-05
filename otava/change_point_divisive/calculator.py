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


from typing import Optional

import numpy as np
from numpy.typing import NDArray

from otava.change_point_divisive.base import Calculator, CandidateChangePoint, WindowedCandidateChangePoint


class PairDistanceCalculator(Calculator):
    def __init__(self, series: NDArray, power: float = 1., window_len: Optional[int] = None):
        super().__init__(series)
        assert 0 < power < 2, f"power={power} isn't in (0, 2)"
        assert window_len is None or window_len >= 2, \
            f"window_len={window_len} must be None (no windowing) or an integer >= 2"
        self.power = power
        self.window_len = window_len
        self.V = None
        self.H = None
        self.distances = None
        self.CS = None

    def _calculate_distances(self):
        """Precomputes the matrix of pairwise distances:
            distances(i, j) = |series[i] - series[j]| ** power.
        """
        if self.distances is None:
            self.distances = np.power(np.abs(self.series[:, None] - self.series[None, :]), self.power)

    def _ensure_cumulative_distances(self):
        """Precomputes `CS`, the zero-padded two-dimensional cumulative sum of the
        `distances` matrix:
                        CS(i, j) = Σ distances[0:i, 0:j],
        so that the sum over any axis-aligned block of `distances` is
                Σ distances[a:b, c:d] = CS(b, d) - CS(a, d) - CS(b, c) + CS(a, c).

        The windowed evaluation of the `Q` function (see `_get_windowed_candidate`)
        only ever needs such block sums, taken entirely inside a `window_len`-sized
        neighborhood of the candidate change point.
        """
        if self.CS is None:
            self._calculate_distances()
            n = len(self.series)
            padded = np.zeros((n + 1, n + 1))
            padded[1:, 1:] = self.distances
            self.CS = padded.cumsum(axis=0).cumsum(axis=1)

    def _calculate_pairwise_differences(self):
        '''Precomputes `H` and `V` functions that are used for computation of `Q` function.
            See more details about `Q` function in `get_candidate_change_point` method.
            See more details about the use of `H` and `V` functions in `_get_A_B_C` method.

        Let matrix `distances` be a matrix of all possible L1 (Manhattan) distances between
        elements of 1d array `series`. If `D(i, j) = |series[i] - series[j]|` and `N = len(series)`,
        then

                      | D(0, 0)        D(0, 1)      …       D(0, N - 1) |
                      | D(1, 0)        D(1, 1)      …       D(1, N - 1) |
        distances =   |    ⋮              ⋮          ⋱         ⋮        | .
                      | D(N - 1, 0)    D(N - 1, 1)  …   D(N - 1, N - 1) |

        Note that the main diagonal of the matrix is filled with 0.


        We define functions `V` and `H` as the following (V)ertical and (H)orizontal
        cummulative sums:
                        V(start, τ, κ) = Σ distances[start:τ, τ],
                        H(start, τ, κ) = Σ distances[τ, τ:κ],
        for `start < τ < κ <= N`.
        Note that `V(start, τ, κ) = V(start, τ)` and `H(start, τ, κ) = H(τ, κ)`.


        Vector V contains the following values of function `V(start, τ, κ)`:
                            V = [V(0, 1, κ)     V(0, 2, κ),    …  V(0, N - 1, κ)].
            `V(0, 0, κ) = 0` so they are ommited. As noted, function `V(start, τ, κ)`
            does not depend on `κ`. Therefore, vector V contains all values of function
            `V(0, τ, κ)`. We can easily get values of function `V` for an arbitrary
            value of `start` by
                            V(start, τ, κ) = V(0, τ, κ) - Σ distances[0 : start, τ].
        Note: The reason not all values of `V(start, τ, κ)` are precomputed is that
              we do not need them all. The values of `start` will depend on critical
              points we find. Precomuting them for all possible values is a waste.


        Matrix H contains the following values of function `H(start, τ, κ)`:

                  | H(start, 0, 2)    H(start, 0, 3)   …  H(start, 0, N)     |
                  |          0        H(start, 1, 3)   …  H(start, 1, N)     |
            H =   |          ⋮                 ⋮        ⋱          ⋮         | .
                  |          0                 0       …  H(start, N - 2, N) |

            `H(start, x, x) = H(start, x - 1, x) = 0` for any `x` so they are ommited.
            As noted, function `H(start, τ, κ)` does not depend on `start`. Therefore,
            matrix H contains all possible values of function `H`.
        Note: We precomputed all values of `H(start, τ, κ)` because all of them are needed
              for the very first iteration (`start=0` and `end=N`).'''
        self._calculate_distances()
        triu = np.triu(self.distances, k=1)[:-1, 1:]
        self.V = triu.sum(axis=0)
        self.H = triu.cumsum(axis=1)

    def _get_Q_vals(self, start: int, end: int) -> NDArray:
        '''Computes matrices A, B, C where all possible values of function `Q` are
        given by matrix Q = A - B - C.
        See more details about `Q` function in `get_candidate_change_point` method.

        For any given `start` and `end` let
                        Q(τ, κ) = A(start, τ, κ) - B(start, τ, κ) - C(start, τ, κ),
        where `start < τ < κ <= end`. (For definitions of `A`, `B`, `C` see
        formula of `Q` in `get_candidate_change_point` method.) All possible values of function
        `A` are given by matrix

              | A(start, start + 1, start + 2)    A(start, start + 1, start + 3)   …  A(start, start + 1, end) |
              |                0                  A(start, start + 2, start + 3)   …  A(start, start + 2, end) |
        A =   |                ⋮                                  ⋮                 ⋱                 ⋮          | .
              |                0                                  0                …  A(start, end - 1, end)  |

        Matrices B and C follow the same index-to-value pattern.

        Matrices A, B, and C are used to compute values of function `Q` recursively, without
        recomputing the same sums over and over again. The recursive formulas were further
        transformed to closed forms, so they can be computed using numpy cummulative sum
        function to take advantage of numpy vectorized operations. (Note that each column
        in matrices A, B, C can be repersented through np.cumsum). The formulas use
        commulative sum of functions `H` and `V`, which definitions can be found in
        `_calculate_pairwise_differences` method.

            A(start, τ, κ) = 2 / (κ - s) * (Σt=start,τ-1  H(start, t, κ) - Σt=start+1,τ-1  V(start, t, κ)),

            B(start, τ, κ) = 2 * (κ - τ) / (κ - start) / (τ - start - 1) * Σt=start+1,τ-1  V(start, t, κ),

            C(start, τ, κ) = 2 * (τ - start) / (κ - start) / (κ - τ - 1) * Σt=τ,κ-2  H(start, t, κ).'''
        if self.V is None or self.H is None:
            self._calculate_pairwise_differences()

        V = self.V[start : end - 1] - self.distances[0 : start, start + 1 : end].sum(axis=0)
        H = self.H[start : end - 1, start : end - 1]

        taus = np.arange(start + 1, end)[:, None]
        kappas = np.arange(start + 2, end + 1)[None, :]

        A = np.zeros((end - 1 - start, end - 1 - start))
        A_coefs = 2 / (kappas - start)
        A[1:, :] = np.cumsum(V)[:-1, None]
        A = A_coefs * np.triu(np.cumsum(H, axis=0) - A, k=0)

        B = np.zeros((end - 1 - start, end - 1 - start))
        B_num = 2 * (kappas - taus)
        B_den = (kappas - start) * (taus - start - 1)
        B_mask = np.triu(np.ones_like(B_den, dtype=bool), k=0)
        B_out = np.zeros_like(B_den, dtype=float)
        B_coefs = np.divide(B_num, B_den, out=B_out, where=B_mask & (B_den != 0))
        B[1:, 1:] = B_coefs[1:, 1:] * np.cumsum(V)[:-1, None]

        C = np.zeros((end - 1 - start, end - 1 - start))
        C_num = 2 * (taus - start)
        C_den = (kappas - start) * (kappas - taus - 1)
        C_mask = np.triu(np.ones_like(C_den, dtype=bool), k=1)
        C_out = np.zeros_like(C_den, dtype=float)
        C_coefs = np.divide(C_num, C_den, out=C_out, where=C_mask & (C_den != 0))
        C[:-1, 1:] = C_coefs[:-1, 1:] * np.flipud(np.cumsum(np.flipud(H[1:, 1:]), axis=0))

        # Element of matrix `Q_{i, j}` is equal to `Q(τ, κ) = Q(i + 1, j + 2) = QQ(sequence[start : i + 1], sequence[i + 1 : j + 2])`.
        # So, critical point is `τ = i + 1`.
        return A - B - C

    def _get_windowed_candidate(self, start: int, end: int) -> CandidateChangePoint:
        '''Finds the potential critical point of `series[start:end]` under the `window_len`
        constraint, without materializing the full `(τ, κ)` matrix of `Q` values.

        The window constraint (issue #84) localizes the `Q` function around every
        candidate change point `τ`: the split is evaluated as
                        Q_w(τ, κ) = QQ(series[L : τ], series[τ : κ]),
        where
                        L = max(start, τ - ⌊window_len / 2⌋)  and  κ <= min(end, τ + ⌊window_len / 2⌋),
        i.e. both sides of the split are limited to `⌊window_len / 2⌋` neighboring
        points. All the normalizing factors of `QQ` use these window-local boundaries
        (`L` and `κ`), so `Q_w` is exactly the `Q` function of the (shorter) sequence
        `series[L : κ]` split at `τ`. Note that `window_len >= 2 * (end - start)` makes
        the constraint inactive: `L = start` and `κ <= end` for every `τ`, so `Q_w`
        coincides with the unwindowed `Q` of `_get_Q_vals`.

        Instead of the full `O((end - start)^2)` matrix, this method evaluates `Q_w`
        only on the window band: `κ - τ <= ⌊window_len / 2⌋`. The band is swept along
        its short side: for every offset `d = κ - τ` in `1 .. ⌊window_len / 2⌋` all
        the `Q_w(τ, τ + d)` values are computed vectorized over `τ`. Every per-`d`
        step needs only block sums of the `distances` matrix (see
        `_ensure_cumulative_distances`), so the whole scan costs
        `O((end - start) * window_len)` time with `O(window_len)` numpy operations.
        '''
        half = self.window_len // 2
        self._ensure_cumulative_distances()
        CS = self.CS

        best_index = None
        best_q = -np.inf
        best_window = None

        # within_right(τ, d) = Σ distances[τ:τ+d, τ:τ+d], accumulated over d;
        # appending the τ+d-1-th row AND column adds two symmetric triangles:
        # 2 * Σ distances[τ+d-1, τ:τ+d-1]
        within_right = np.zeros(end - start)
        between = np.zeros(end - start)   # between(τ, d) = Σ distances[max(start, τ-half):τ, τ:τ+d]

        for d in range(1, half + 1):
            taus = np.arange(start + 1, end - d + 1)          # valid τ for this offset: τ + d <= end
            if taus.size == 0:
                break
            left = np.maximum(start, taus - half)
            r = taus + d - 1                                   # last row/col index of the [τ:κ) block

            # A-term numerator, incremental over d: one new column of the
            # between-block per step: Σ distances[left(τ):τ, τ+d-1]
            col = (CS[taus, r + 1] - CS[left, r + 1] - CS[taus, r] + CS[left, r])
            between[taus - start - 1] += col
            # C-term numerator, incremental over d: two symmetric triangles
            row = 2.0 * (CS[r + 1, r] - CS[r, r] - CS[r + 1, taus] + CS[r, taus])
            within_right[taus - start - 1] += row

            n = taus - left                                    # size of series[left:tau], vector
            m = d                                              # size of series[tau:tau+d]
            denom = n + m
            within_left = CS[taus, taus] - CS[left, taus] - CS[taus, left] + CS[left, left]

            Q = 2.0 * between[taus - start - 1] / denom
            has_left = n > 1
            Q[has_left] -= m * within_left[has_left] / (denom[has_left] * (n[has_left] - 1))
            if m > 1:
                Q -= n * within_right[taus - start - 1] / (denom * (m - 1))

            best = int(np.argmax(Q))
            if Q[best] > best_q:
                best_q = float(Q[best])
                best_index = int(taus[best])
                best_window = slice(int(left[best]), int(taus[best]) + d)

        return WindowedCandidateChangePoint(index=best_index, qhat=best_q, window=best_window)

    def _get_Q_vals_windowed(self, start: int, end: int) -> NDArray:
        '''All values of the windowed `Q_w(τ, κ)` function (see `_get_windowed_candidate`)
        as a full matrix, with `-inf` outside the `window_len` band.

        Every entry is computed independently, directly from block sums of the
        `distances` matrix. This is O((end - start)^2) time, so it is meant for
        testing and visualization only - `_get_windowed_candidate` is the production
        path. The two methods are written independently on purpose, so that their
        agreement is a real cross-check.
        '''
        half = self.window_len // 2
        self._ensure_cumulative_distances()
        CS = self.CS

        size = end - start - 1
        Q = np.full((size, size), -np.inf)
        for tau in range(start + 1, end):
            left = max(start, tau - half)
            for kappa in range(tau + 1, min(end, tau + half) + 1):
                n, m = tau - left, kappa - tau
                between = CS[tau, kappa] - CS[left, kappa] - CS[tau, tau] + CS[left, tau]
                value = 2.0 * between / (kappa - left)
                if n > 1:
                    within_left = CS[tau, tau] - CS[left, tau] - CS[tau, left] + CS[left, left]
                    value -= m * within_left / ((kappa - left) * (n - 1))
                if m > 1:
                    within_right = CS[kappa, kappa] - CS[tau, kappa] - CS[kappa, tau] + CS[tau, tau]
                    value -= n * within_right / ((kappa - left) * (m - 1))
                Q[tau - start - 1, kappa - start - 2] = value
        return Q

    def get_candidate_change_point(self, interval: slice) -> CandidateChangePoint:
        '''For a given `slice(start, end)` finds potential critical point in subsequence series[slice],
        i.e., from index `start` to `end - 1` inclusive.


        The potential critical point is defined as the following.
            Suppose for given `start` and `end` the pair `(τ, κ)` maximizes function
                            Q(τ, κ) = QQ(series[start : τ], series[τ : κ]),
            where `τ` and `κ` are such that both `series[start : τ]` and `series[τ : κ]` are non-empty.
            Then `τ` is a potential critical point (i.e., the first element of `series[τ : κ]`).
        Note: for `series[start:τ]` and `series[τ:κ]` to be non-empty, we have
                            start < τ < κ <= end = len(series).
        Note: start < τ => sequence[0] cannot be a critical point.


        Function `QQ` is defined as the following:
            Let `Z` be a series `[Z_{start}, Z_{start + 1}, ..., Z_{end}]`, and `X` and `Y`
            be a split of `Z`, i.e.,
                            X = [Z_{start}, Z_{start + 1}, ..., Z_{a - 1}] = [X_1, X_2, ..., X_n],
                            Y = [Z_{a}, Z_{a + 1}, ..., Z_{b - 1}] = [Y_1, Y_2, ..., Y_m],
            where `start < a - 1 < b - 1 <= end`.
            Then
                            QQ(X, Y) = 2 / (m + n) * Σi=1,n Σj=1,m |X_i - Y_j|
                                      - 2 * m / (m + n) / (n - 1) * Σ1<=i<k<=n |X_i - X_k|
                                      - 2 * n / (m + n) / (m - 1) * Σ1<=j<k<=m |Y_j - Y_k|.

            Note: QQ(X, Y) = QQ(Z[start : a], Z[a : b]) = Q(a, b).


        If the calculator was constructed with a `window_len`, the potential critical
        point is defined the same way, except that both sides of the split are limited
        to `⌊window_len / 2⌋` neighboring points of `τ` (see `_get_windowed_candidate`).

        This method computes all values of `Q` for given `start` and `end`, and returns index
        of the potential critical point and the maximized value of `Q`.'''

        start = 0 if interval.start is None else interval.start
        end = len(self.series) if interval.stop is None else interval.stop
        assert end - start > 1, f"interval must be a non-empty slice, but array[{start}:{end}] was given."

        if self.window_len is None:
            Q = self._get_Q_vals(start, end)
            i, j = np.unravel_index(np.argmax(Q), Q.shape)
            return CandidateChangePoint(index=i + 1 + start, qhat=Q[i][j])
        return self._get_windowed_candidate(start, end)
