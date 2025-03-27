
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

from otava.analysis import compute_change_points


def _get_series():
    """
    This is the Tigerbeetle dataset used for demo purposes at Nyrkiö.
    It has a couple distinctive ups and down, ananomalous drop, then an upward slope and the rest is just normal variance.

    ^                                                                             .'
    |            ...       ,..''.'...,......''','....'''''.......'...'.....,,,..''
    |..  ..     |   |....''
    |  ||  |,,..|
    |  ||
    |  ;
    +------------------------------------------------------------------------------------->
      10  16    71  97
    """
    return [26705, 26475, 26641, 26806, 26835, 26911, 26564, 26812, 26874, 26682, 15672, 26745, 26460, 26977, 26851, 23412, 23547, 23674, 23519, 23670, 23662, 23462, 23750, 23717, 23524, 23588, 23687, 23793, 23937, 23715, 23570, 23730, 23690, 23699, 23670, 23860, 23988, 23652, 23681, 23798, 23728, 23604, 23523, 23412, 23685, 23773, 23771, 23718, 23409, 23739, 23674, 23597, 23682, 23680, 23711, 23660, 23990, 23938, 23742, 23703, 23536, 24363, 24414, 24483, 24509, 24944, 24235, 24560, 24236, 24667, 24730, 28346, 28437, 28436, 28057, 28217, 28456, 28427, 28398, 28250, 28331, 28222, 28726, 28578, 28345, 28274, 28514, 28590, 28449, 28305, 28411, 28788, 28404, 28821, 28580, 27483, 26805, 27487, 27124, 26898, 27295, 26951, 27312, 27660, 27154, 27050, 26989, 27193, 27503, 27326, 27375, 27513, 27057, 27421, 27574, 27609, 27123, 27824, 27644, 27394, 27836, 27949, 27702, 27457, 27272, 28207, 27802, 27516, 27586, 28005, 27768, 28543, 28237, 27915, 28437, 28342, 27733, 28296, 28524, 28687, 28258, 28611, 29360, 28590, 29641, 28965, 29474, 29256, 28611, 28205, 28539, 27962, 28398, 28509, 28240, 28592, 28102, 28461, 28578, 28669, 28507, 28535, 28226, 28536, 28561, 28087, 27953, 28398, 28007, 28518, 28337, 28242, 28607, 28545, 28514, 28377, 28010, 28412, 28633, 28576, 28195, 28637, 28724, 28466, 28287, 28719, 28425, 28860, 28842, 28604, 28327, 28216, 28946, 28918, 29287, 28725, 29148, 29541, 29137, 29628, 29087, 28612, 29154, 29108, 28884, 29234, 28695, 28969, 28809, 28695, 28634, 28916, 29852, 29389, 29757, 29531, 29363, 29251, 29552, 29561, 29046, 29795, 29022, 29395, 28921, 29739, 29257, 29455, 29376, 29528, 28909, 29492, 28984, 29621, 29026, 29457, 29102, 29114, 28924, 29162, 29259, 29554, 29616, 29211, 29367, 29460, 28836, 29645, 29586, 28848, 29324, 28969, 29150, 29243, 29081, 29312, 28923, 29272, 29117, 29072, 29529, 29737, 29652, 29612, 29856, 29012, 30402, 29969, 29309, 29439, 29285, 29421, 29023, 28772, 29692, 29416, 29267, 29542, 29904, 30045, 29739, 29945, 29141, 29163, 29765, 29197, 29441, 28910, 29504, 29614, 29643, 29506, 29420, 29672, 29432, 29784, 29888, 29309, 29247, 29816, 29254, 29813, 29451, 29382, 29618, 28558, 29845, 29499, 29283, 29184, 29246, 28790, 29952, 29145, 29415, 30437, 29227, 29605, 29859, 29156, 29807, 29406, 29734, 29861, 29140, 29983, 29832, 29919, 29896, 29991, 29266, 29001, 29459, 29548, 29310, 29042, 29303, 29894, 29091, 29018, 29537, 29614, 29180, 29736, 29500, 29218, 29581, 28906, 28542, 29306, 28987, 29878, 28865, 30272, 29707, 29662, 29815, 30492, 29347, 30096, 29054, 30238, 28813, 31895, 28915]


def _actual_t_est(p, m=0.0, w=30, new_data=None):
    series = _get_series()
    cps, old_weak_cp = compute_change_points(series, window_len=w, max_pvalue=p, min_magnitude=m, new_data=new_data)

    if new_data is not None and new_data == 0:
        cps, old_weak_cp = compute_change_points(series, window_len=w, max_pvalue=p, min_magnitude=m, new_data=None)

    if new_data:
        cps, old_weak_cp = compute_change_points(series, window_len=w, max_pvalue=p, min_magnitude=m, new_data=new_data, old_weak_cp=old_weak_cp)


def test_tb_baseline0001(benchmark):
    benchmark(_actual_t_est, 0.0001)


def test_tb_baseline001(benchmark):
    benchmark(_actual_t_est, 0.001)


def test_tb_baseline01(benchmark):
    benchmark(_actual_t_est, 0.01)


def test_tb_baseline1(benchmark):
    benchmark(_actual_t_est, 0.1)


def test_tb_baseline2(benchmark):
    benchmark(_actual_t_est, 0.2)


def test_tb_twice0001(benchmark):
    benchmark(_actual_t_est, 0.0001, new_data=0)


def test_tb_twice001(benchmark):
    benchmark(_actual_t_est, 0.001, new_data=0)


def test_tb_twice01(benchmark):
    benchmark(_actual_t_est, 0.01, new_data=0)


def test_tb_twice1(benchmark):
    benchmark(_actual_t_est, 0.1, new_data=0)


def test_tb_twice2(benchmark):
    benchmark(_actual_t_est, 0.2, new_data=0)


def test_tb_incremental0001(benchmark):
    benchmark(_actual_t_est, 0.0001, new_data=1)


def test_tb_incremental001(benchmark):
    benchmark(_actual_t_est, 0.001, new_data=1)


def test_tb_incremental01(benchmark):
    benchmark(_actual_t_est, 0.01, new_data=1)


def test_tb_incremental1(benchmark):
    benchmark(_actual_t_est, 0.1, new_data=1)


def test_tb_incremental2(benchmark):
    benchmark(_actual_t_est, 0.2, new_data=1)
