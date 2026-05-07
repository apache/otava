
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

from otava.analysis import compute_change_points_deterministic
from tests.tigerbeetle_test import tigerbeetle_demo_data as _get_series


def test_tb_old_defaults():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.01, min_magnitude=0.05)
    indexes = [c.index for c in cps]
    assert indexes == [15, 71]


def test_tb_old_defaults_p05():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.05, min_magnitude=0.05)
    indexes = [c.index for c in cps]
    assert indexes == [15, 71]


def test_tb_old_defaults_p1():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.1, min_magnitude=0.05)
    indexes = [c.index for c in cps]
    assert indexes == [15, 71]


def test_tb_old_defaults_p2():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.2, min_magnitude=0.05)
    indexes = [c.index for c in cps]
    assert indexes == [10, 11, 15, 71]


def test_tb_small_threshold_p1():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.1, min_magnitude=0.01)
    indexes = [c.index for c in cps]
    assert indexes == [15, 49, 58, 61, 71, 95, 117, 131, 148, 192, 206, 212, 250, 260, 363]


def test_tb_magnitude0_p2():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.2)
    indexes = [c.index for c in cps]
    assert indexes == [3, 5, 6, 7, 9, 10, 11, 13, 15, 26, 41, 44, 45, 47, 48, 49, 56, 58, 60, 61, 71, 72, 74, 76, 79, 82, 95, 114, 116, 117, 124, 125, 126, 127, 129, 131, 142, 148, 187, 189, 190, 192, 206, 212, 249, 250, 251, 260, 363]


def test_tb_magnitude0_p15():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.15)
    indexes = [c.index for c in cps]
    assert indexes == [3, 10, 11, 13, 15, 26, 41, 44, 45, 47, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 187, 189, 190, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p14():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.14)
    indexes = [c.index for c in cps]
    assert indexes == [3, 10, 11, 13, 15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 187, 189, 190, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p13():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.13)
    indexes = [c.index for c in cps]
    assert indexes == [3, 10, 11, 13, 15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 187, 189, 190, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p127():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.129)
    indexes = [c.index for c in cps]
    assert indexes == [3, 10, 11, 13, 15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 187, 189, 190, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p125():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.125)
    indexes = [c.index for c in cps]
    assert indexes == [15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p12():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.12)
    indexes = [c.index for c in cps]
    assert indexes == [15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p11():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.11)
    indexes = [c.index for c in cps]
    assert indexes == [15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p1():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.1)
    indexes = [c.index for c in cps]
    assert indexes == [15, 26, 41, 44, 48, 49, 56, 58, 60, 61, 71, 82, 95, 117, 131, 142, 148, 192, 206, 212, 249, 250, 260, 363]


def test_tb_magnitude0_p05():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.05)
    indexes = [c.index for c in cps]
    assert indexes == [15, 61, 71, 82, 95, 117, 131, 192, 206, 212, 249, 260, 363]


def test_tb_magnitude0_p02():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.02)
    indexes = [c.index for c in cps]
    assert indexes == [15, 61, 71, 82, 95, 117, 131, 192, 206, 212, 249, 260, 363]


def test_tb_magnitude0_p01():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.01)
    indexes = [c.index for c in cps]
    assert indexes == [15, 61, 71, 82, 95, 117, 131, 192, 212, 249, 260, 363]


def test_tb_magnitude0_p001():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.001)
    indexes = [c.index for c in cps]
    assert indexes == [15, 61, 71, 192, 212, 260]


def test_tb_magnitude0_p0001():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.0001)
    indexes = [c.index for c in cps]
    assert indexes == [15, 61, 71, 192, 260]


def test_tb_magnitude0_p00001():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.00001)
    indexes = [c.index for c in cps]
    print(cps)
    assert indexes == [15, 61, 71, 192, 260]


def test_tb_magnitude0_p7x01():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.00000001)
    indexes = [c.index for c in cps]
    print(cps)
    assert indexes == [71, 192]


def test_tb_magnitude0_p31x01():
    series = _get_series()
    cps, weak_cps = compute_change_points_deterministic(series, max_pvalue=0.00000000000000000000000000000001)
    indexes = [c.index for c in cps]
    print(cps)
    assert indexes == [71, 192]
