<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 -->

# Change Point Detection
## Overview
Apache Otava implements a nonparametric change point detection algorithm designed to identify statistically significant distribution changes in time-ordered data. The method is primarily based on the **E-Divisive family of algorithms** for multivariate change point detection, with some practical adaptations.

At a high level, the algorithm:
- Measures statistical divergence between segments of a time series
- Searches for change points using hierarchical segmentation
- Evaluates significance of candidate splits using statistical hypothesis testing

The current implementation prioritizes:
- Robustness to noisy real-world signals
- Deterministic behavior
- Practical runtime for production workloads

A representative example of algorithm application:

![Figure 1. Example](./imgs/example.png "Example")

Figure 1. An example of running [compute_change_points](https://github.com/apache/otava/tree/master/otava/analysis.py) function on [Tigerbeetle dataset](https://github.com/apache/otava/tree/master/tests/tigerbeetle_test.py). The parameters for the `compute_change_points` function are displayed in the bottom right corner. Here the algorithm detected 5 change points with a statistical test showing that behavior of the time series changes at those points. In other words, the data have different distributions to the left and to the right of each change point.

With that being said, the difference could be merely a change in the mean, but the algorithm isn't restricted to that and could also detect other kinds of changes, such as a change in variance, skewness, and other shifts in the overall shapes between the distributions even if the mean stays constant. Once potential change points are identified, a statistical test is performed to validate which of the points are in fact change points. That is to say, they are statistically significant. The user gets to choose the threshold (also called p-value threshold or significance threshold) used for the statistical test. The threshold adjusts the balance between finding fewer change points and finding false positives. For example, a p-value threshold of 0.01 roughly means that there will be at most 1% false positives. The false negatives are harder to estimate and depend on both the chosen threshold and the actual data distribution.

## Technical Details
### Main Idea
The main idea is to use a divergence measure between distributions to identify potential points in time series at which the characteristics of the time series change. Namely, having a time series $Z = \\{Z_0, \cdots, Z_{T-1}\\}$ (which may be multidimensional, i.e. from $\mathbb{R}^d$ with $d\geq1$) we are testing non-empty subsequences $X_\tau = \\{ Z_0, Z_1, \cdots, Z_{\tau-1} \\}$ and $Y_\tau(\kappa)=\\{ Z_\tau, Z_{\tau+1}, \cdots, Z_{\kappa-1} \\}$ for all possible $1 \leq \tau < \kappa \leq T$ to find such $\hat{\tau}, \hat{\kappa}$ that maximize the probability that $X_\tau$ and $Y_\tau(\kappa)$ come from different distributions. If the probability for the best found $\hat{\tau}, \hat{\kappa}$ is above a certain threshold, then the candidate $\hat{\tau}$ is a change point. The process is repeated recursively to the left and to the right of $\hat{\tau}$ until no candidate corresponds to a high enough probability. This process yields a series of change points $1 \leq \hat{\tau}_1 < \cdots < \hat{\tau}_k \leq T - 1$. See an example in Figure 2.

![Figure 2. Main Idea](./imgs/main_idea.png "Main Idea")

Figure 2. On the **left subfigure**, there is a time-series $Z=\\{ Z_0, \cdots Z_{21}\\}$ in red color, with two subseries $X_6 = \\{ Z_0, \cdots, Z_5 \\}$ in green and $Y_6(12) = \\{Z_6, \cdots, Z_{11}\\}$ in blue. Among all possible consecutive subseries, the subseries $X_6$ and $Y_6(12)$ have the highest probability to come from different distributions, i.e., being the most distinct. These subseries are defined by the pair $`(\hat{\tau}_1, \hat{\kappa}_1) = (6, 12)`$. If the difference between these subsequences is big enough (above the significance threshold), then $`\hat{\tau}_1=6`$ is a change point, and the algorithm will continue to the next step with the next best pair being $`(\hat{\tau}_2, \hat{\kappa}_2) = (12, 22)`$. Note that the $\kappa$ defines the end of the subseries $Y_\tau(\kappa)$, which might be before the end of series $Z$, i.e., $\kappa \leq T$. The reason can be seen on the **right subfigures**. Specifically, it shows that if we restrict the $Y$ subseries so that it does not go all the way to the end of series $Z$, the algorithm might detect the changes in time series $Z$ better. Consider a loosely defined distance between the distributions (cyan) in the **top right subfigure** $X_6$ vs $Y_6(12)$ and in the **bottom right subfigure** $X_6$ vs $Y_6(22)$. The tail $\\{ Z_{12}, \cdots Z_{21} \\}$ in $Y_6(22)$ muddies the signal, compared to the truncated series $Y_6(12)$.

There are a couple of additional nuances and notes that we want to mention:
- According to the provided definition, the change point is the first point of the *second* subsequence, and, because both subsequences must be non-empty, the change point cannot be the first point of the whole sequence $Z$, i.e., point $Z_0$.
  - There exists an alternative way of defining the change point (as the last point of the first subsequence - in that case, the last point $Z_{T-1}$ cannot be the change point). And, in fact, some of the papers cited here are using that other definition. However, Apache Otava uses the term "change point" as defined above, i.e., the change point is the first commit at which metrics change.
- In the example in Figure 2 we effectivelly used distance between means as a distance between the distributions. It's an oversimplification for illustrative purposes, and in reality we actually use a divergence measure between multivariate distributions. See **[Original Work](#original-work)** section for more details.
- In the example in Figure 2, we compared only two pairs of the values $(\hat{\tau}_1, \hat{\kappa}_1)$, namely $(6, 12)$ and $(6, 22)$. The algorithm actually checks for all valid values before choosing the best one. See Figure 3.
![Figure 3. Tau-Kappa](./imgs/tau_kappa.png "Tau Kappa")

Figure 3. Divergence measure between distributions of $X_\tau$ and $T_\tau(\kappa)$ for all valid values of $(\tau, \kappa)$. The biggest number corresponds to the most promising pair of values (marked by a red cross).

### Original Work
The original work was presented in [*"A Nonparametric Approach for Multiple Change Point Analysis of Multivariate Data" by Matteson and James*](https://arxiv.org/abs/1306.4933). The authors provided extensive theoretical reasoning on using the following empirical divergence measure:

$\hat{𝒬}(X_\tau,Y_\tau(\kappa);\alpha)=\dfrac{\tau(\kappa - \tau)}{\kappa}\hat{ℰ}(X_\tau,Y_\tau(\kappa);\alpha),$

$\hat{ℰ}(X_\tau,Y_\tau(\kappa);\alpha)=\dfrac{2}{\tau(\kappa - \tau)}\sum\limits_{i=0}^{\tau-1}\sum\limits_{j=\tau}^{\kappa-1} \|Z_i - Z_j\|^\alpha - {\displaystyle \binom{\tau}{2}^{-1}} \sum\limits_{0\leq i < j \leq\tau-1}\|Z_i - Z_j\|^\alpha - {\displaystyle \binom{\kappa - \tau}{2}^{-1}} \sum\limits_{\tau\leq i < j \leq\kappa-1}\|Z_i - Z_j\|^\alpha,$

where $\alpha \in (0, 2)$, usually we take $\alpha=1$; $\|\cdot\|$ is Euclidean distance; and the coefficient in front of the second and third terms in $\hat{ℰ}$ are reciprocals of binomial coefficients. The idea behind each term in $\hat{ℰ}$ is actually quite simple. The first term of $\hat{ℰ}$ is the average of all possible pairwise distances between subsequences $X_\tau$ and $Y_\tau(\kappa)$. The second and third terms are the average of all possible pairwise distances of points within subsequences $X_\tau$ and $Y_\tau(\kappa)$, respectively. The intuition behind this divergence measure is to compare "how large" is the distance between the distributions, compared to the distances within each distribution on average. And the coefficient in front of $\hat{ℰ}$ in $\hat{𝒬}$ is a normalization coefficient that is required for some theoretical results to work.

The most "dissimilar" subsequences are given by

$(\hat{\tau}, \hat{\kappa}) = \text{arg}\max\limits_{(\tau, \kappa)}\hat{𝒬}(X_\tau,Y_\tau(\kappa);\alpha).$

After the subsequences are found, one needs to find the probability that $X_{\hat{\tau}}$ and $Y_{\hat{\tau}}(\hat{\kappa})$ come from different distributions. Generally speaking, the time sub-series $X$ and $Y$ could come from any distribution(s), and the authors proposed the use of a non-parametric permutation test to test for significant difference between them. If the candidates are shown to be significant, the process is to be run using hierarchical segmentation, i.e., recursively. For more details read the linked paper.

### Hunter Paper
While the original paper was theoretically sound, there were a few practical issues with the methodology. They were outlined clearly in [*Hunter: Using Change Point Detection to Hunt for Performance Regressions by Fleming et al.*](https://arxiv.org/abs/2301.03034). Here is the short outline, with more details in the linked paper:
- High computational cost due to the permutation significance test.
- Non-determinism of the results due to the permutation significance test.
- Missing change points in some of the patterns as the time series expands.

The authors proposed a few innovations to resolve the issues. Namely,
1. **Faster significance test:** replace permutation test with Student's t-test, that demonstrated great results in practice - *This helps reduce computational cost and non-determinism*.
2. **Fixed-Sized Windows:** Instead of looking at the whole time series, the algorithm traverses it through an overlapping sliding window approach - *This helps catch special pattern-cases described in the paper*.
3. **Weak Change Points:** Having two significance thresholds. Algorithm starts with a more relaxed threshold to identify a larger set of candidate change points, called "weak" change points, and then continues by re-evaluating all "weak" change points using stricter threshold to yield the final change points - *Using a single threshold could have myopically stopped the algorithm. Allowing it to look for more points and filter out the "weak" ones later resolves the issue.*

### Apache Otava Implementation
The current implementation in Apache Otava is conceptually the one from the Hunter paper with a newly rewritten implementation of the algorithm.

Starting with a zero-indexed time series $Z = \\{Z_0, Z_1, \cdots, Z_{T-1} \\}$, we are interested in computing $\hat{𝒬}(X_\tau,Y_\tau(\kappa);\alpha)$. Moreover, because we are going to recursively split the time series, the series in the arguments of the function $𝒬$ do not have to start from the beginning of the series. For simplicity, let us fix $\alpha=1$ and define the following function instead:

$Q(s, \tau, \kappa) = \left.𝒬(\\{Z_s, Z_{s+1}, \dots, Z_{\tau-1}\\}, \\{Z_\tau, Z_{\tau + 1}, \cdots, Z_{\kappa-1}\\}; \alpha)\right|_{\alpha=1},$

which is equivalent to comparing the time series slices `Z[s:tau]` and `Z[tau:kappa]` in Python notation. Next, let us define a symmetric distance matrix $D$, with $D_{ij} = \|Z_i - Z_j\|$ and the following auxiliary functions:

$V(s, \tau, \kappa) = \sum\limits_{i=s}^{\tau-1} D_{i\tau},$

$H(s, \tau, \kappa) = \sum\limits_{j=\tau}^{\kappa-1} D_{\tau j}.$

Note that $V(s, \tau, \kappa) = V(s, \tau, \cdot)$ and $H(s, \tau, \kappa) = H(\cdot, \tau, \kappa)$.
Finally, we can use function $V$ and $H$ to define recurrence equations for $Q$. We start by rewriting the function $Q$ as a sum of three functions:

$Q(s, \tau, \kappa) = A(s, \tau, \kappa) - B(s, \tau, \kappa) - C(s, \tau, \kappa),$

Here, functions $A$, $B$, $C$ correspond to the average pairwise distances between and within the subsequences. See **[Original Work](#original-work)** section for more details.

$A(s, \tau, \kappa) = A(s, \tau - 1, \kappa) - \dfrac{2}{\kappa - s} V(s, \tau - 1, \kappa) + \dfrac{2}{\kappa - s} H(s, \tau - 1, \kappa),$

$B(s, \tau, \kappa) = \dfrac{2(\kappa - \tau)}{(\kappa - s)(\tau - s - 1)} \left(\dfrac{(\kappa - s)(\tau - s - 2)}{2 (\kappa - \tau + 1)} B(s, \tau - 1, \kappa) + V(s, \tau - 1, \kappa) \right),$

$C(s, \tau, \kappa) = \dfrac{2(\tau - s)}{(\kappa - s) (\kappa - \tau - 1)} \left( \dfrac{(\kappa - s)(\kappa - \tau - 2)}{2 (\tau + 1 - s)} C(s, \tau + 1, \kappa) - H(s, \tau, \kappa) \right).$

Note that $A(s, s, \kappa)=0$, and $B(s, s, \kappa)=0$, and $C(s, \kappa, \kappa)=0$ because they correspond to empty subsequences. Moreover, $B(s, s + 1, \kappa) = 0$ and $C(s, \kappa - 1, \kappa)=0$ because each of them corresponds to an average pairwise distance within a subsequence consisting of a single point, i.e., each of them is the sum with zero terms. Using that, we can compute values for $A$, $B$, and $C$ iteratively. Note that functions $A$ and $B$ are computed as $\tau$ increases, and function $C$ is computed as $\tau$ decreases. 

These formulas are effectively used in Apache Otava after some NumPy vectorizations. For details see [change_point_divisive/calculator.py](https://github.com/apache/otava/tree/master/otava/change_point_divisive/calculator.py).
