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

"""
Unit tests for the unified ChangePoint class hierarchy in
otava.change_point_divisive.base:

    BaseStats (+ TTestStats / PermutationStats)
    CandidateChangePoint / ChangePoint / ChangePointSerializer
    ChangePointGroup
    ChangePoints / ChangePointsByTime / ChangePointsByMetric
    SignificanceTester.calculate helpers (compare / get_sides / get_intervals)
"""

import numpy as np
import pytest

from otava.change_point_divisive.base import (
    BaseStats,
    CandidateChangePoint,
    ChangePoint,
    ChangePointGroup,
    ChangePoints,
    ChangePointsByMetric,
    ChangePointsByTime,
    ChangePointSerializer,
    SignificanceTester,
)


# Helpers
def make_stats(left=(1.0, 1.0), right=(5.0, 5.0), pvalue=0.01):
    return BaseStats.calculate(list(left), list(right), pvalue)


def make_cp(metric="m", index=3, left=(1.0, 1.0), right=(5.0, 5.0), pvalue=0.01):
    return ChangePoint(
        index=index, qhat=1.0, stats=make_stats(left, right, pvalue), metric=metric
    )


def make_group(time, metric="m", index=3, commit="sha"):
    return ChangePointGroup(
        time=time, attributes={"commit": commit}, changes={metric: make_cp(metric, index)}
    )


# BaseStats
def test_basestats_calculate_means_and_std():
    s = BaseStats.calculate([10.0, 10.0, 10.0], [20.0, 20.0, 20.0], 0.02)
    assert s.mean_1 == 10.0
    assert s.mean_2 == 20.0
    assert s.std_1 == 0.0
    assert s.std_2 == 0.0
    assert s.pvalue == 0.02
    # convenience getters
    assert s.mean_before() == 10.0
    assert s.mean_after() == 20.0
    assert s.stddev_before() == 0.0
    assert s.stddev_after() == 0.0


def test_basestats_single_element_side_has_zero_std():
    s = BaseStats.calculate([5.0], [7.0, 9.0])
    assert s.std_1 == 0.0
    assert s.std_2 > 0.0


def test_basestats_pvalue_defaults_to_one():
    assert BaseStats.calculate([1.0, 1.0], [2.0, 2.0]).pvalue == 1.0
    # out-of-range values are ignored and fall back to 1.0
    assert BaseStats.calculate([1.0, 1.0], [2.0, 2.0], 5.0).pvalue == 1.0
    assert BaseStats.calculate([1.0, 1.0], [2.0, 2.0], -1.0).pvalue == 1.0


def test_basestats_empty_side_raises():
    with pytest.raises(ValueError):
        BaseStats.calculate([], [1.0, 2.0])
    with pytest.raises(ValueError):
        BaseStats.calculate([1.0, 2.0], [])


def test_basestats_relative_change_and_magnitude():
    s = BaseStats.calculate([10.0, 10.0], [20.0, 20.0], 0.01)
    assert s.forward_rel_change() == 1.0
    assert s.backward_rel_change() == -0.5
    assert s.forward_change_percent() == 100.0
    assert s.backward_change_percent() == -50.0
    assert s.change_magnitude() == 1.0


def test_basestats_zero_mean_guard():
    s = BaseStats.calculate([0.0, 0.0], [1.0, 1.0])
    assert s.forward_rel_change() == 0
    assert s.forward_rel_change(value_if_nan=-1) == -1
    s2 = BaseStats.calculate([1.0, 1.0], [0.0, 0.0])
    assert s2.backward_rel_change() == 0


def test_basestats_to_json_keys():
    s = BaseStats.calculate([10.0, 10.0], [20.0, 20.0], 0.02)
    j = s.to_json()
    assert set(j.keys()) == {
        "forward_change_percent",
        "magnitude",
        "mean_before",
        "stddev_before",
        "mean_after",
        "stddev_after",
        "pvalue",
    }
    # values are rendered as strings
    assert all(isinstance(v, str) for v in j.values())


def test_basestats_copy_is_independent_and_keeps_class():
    s = make_stats()
    c = s.copy()
    assert isinstance(c, BaseStats)
    assert c is not s
    assert (c.mean_1, c.mean_2, c.pvalue) == (s.mean_1, s.mean_2, s.pvalue)
    c.mean_1 = 999.0
    assert s.mean_1 != 999.0


# CandidateChangePoint / ChangePoint / ChangePointSerializer
def test_changepoint_from_and_to_candidate():
    candidate = CandidateChangePoint(index=7, qhat=2.5)
    stats = make_stats()
    cp = ChangePoint.from_candidate(candidate, stats)
    assert cp.index == 7
    assert cp.qhat == 2.5
    assert cp.stats is stats

    back = cp.to_candidate()
    assert isinstance(back, CandidateChangePoint)
    assert back.index == 7
    assert back.qhat == 2.5


def test_changepoint_equality_is_NOT_JUST_by_index():
    a = make_cp(index=3)
    b = make_cp(index=3, left=(2.0, 2.0))  # different stats, same index
    c = make_cp(index=4)
    d = make_cp(index=4)
    # assert a == b # Used to be true, but was not meaningful as general equality
    assert a != b
    assert a != c
    assert c == d


def test_changepoint_metric_defaults_to_none():
    cp = ChangePoint(index=1, qhat=0.0, stats=make_stats())
    assert cp.metric is None


def test_changepoint_copy_is_deep():
    cp = make_cp()
    clone = cp.copy()
    assert clone is not None, "copy() must return the new object"
    assert clone is not cp
    assert clone.stats is not cp.stats
    assert clone.index == cp.index
    assert clone.qhat == cp.qhat
    assert clone.metric == cp.metric
    clone.stats.mean_1 = -1.0
    assert cp.stats.mean_1 != -1.0


def test_changepoint_serializer_rounded_json():
    cp = make_cp(metric="m", index=3, left=(10.0, 10.0), right=(20.0, 20.0), pvalue=0.02)
    j = ChangePointSerializer(cp).to_json(rounded=True)
    assert j["metric"] == "m"
    assert j["index"] == 3
    assert j["forward_change_percent"] == "100"
    assert all(isinstance(j[k], str) for k in ("magnitude", "mean_before", "pvalue"))


def test_changepoint_serializer_unrounded_json():
    cp = make_cp(metric="m", index=3, left=(10.0, 10.0), right=(20.0, 20.0), pvalue=0.02)
    j = ChangePointSerializer(cp).to_json(rounded=False)
    assert j["index"] == 3
    assert j["forward_change_percent"] == 100.0
    assert j["mean_before"] == 10.0
    assert j["mean_after"] == 20.0
    assert j["pvalue"] == 0.02


def test_changepoint_to_json_delegates_to_serializer():
    cp = make_cp(metric="m", index=3, left=(10.0, 10.0), right=(20.0, 20.0), pvalue=0.02)
    assert cp.to_json(rounded=False) == ChangePointSerializer(cp).to_json(rounded=False)


# ChangePointGroup
def test_group_getitem_metrics_and_iter():
    g = ChangePointGroup(
        time=1.0,
        attributes={"commit": "abc"},
        changes={"m1": make_cp("m1"), "m2": make_cp("m2")},
    )
    assert g["m1"].metric == "m1"
    assert set(g.metrics()) == {"m1", "m2"}
    assert {cp.metric for cp in g} == {"m1", "m2"}


def test_group_select_metrics():
    g = ChangePointGroup(
        time=1.0,
        attributes={"commit": "abc"},
        changes={"m1": make_cp("m1"), "m2": make_cp("m2")},
    )
    one = g.select_metrics("m1")
    assert set(one.metrics()) == {"m1"}
    # accepts a list too
    assert set(g.select_metrics(["m1", "m2"]).metrics()) == {"m1", "m2"}
    # the original is untouched
    assert set(g.metrics()) == {"m1", "m2"}


def test_group_set_adds_metric():
    g = make_group(1.0, metric="m1")
    g.set("m2", make_cp("m2"))
    assert set(g.metrics()) == {"m1", "m2"}


def test_group_commit_and_datetime():
    g = ChangePointGroup(time=0.0, attributes={"commit": "deadbeef"}, changes={"m": make_cp()})
    assert g.commit() == "deadbeef"
    # 0.0 epoch seconds -> 1970, in UTC
    assert g.datetime().year == 1970


def test_group_to_json():
    g = make_group(1.0, metric="m", commit="abc")
    j = g.to_json()
    assert j["time"] == 1.0
    assert j["attributes"] == {"commit": "abc"}
    assert isinstance(j["changes"], list) and len(j["changes"]) == 1
    assert j["changes"][0]["metric"] == "m"


def test_group_copy_is_deep():
    g = make_group(1.0, metric="m", commit="abc")
    clone = g.copy()
    assert isinstance(clone.attributes, dict)
    assert isinstance(clone.changes, dict)
    assert clone.attributes == {"commit": "abc"}
    assert set(clone.metrics()) == {"m"}
    # deep: mutating the clone's change does not touch the original
    clone.changes["m"].stats.mean_1 = -1.0
    assert g.changes["m"].stats.mean_1 != -1.0


# ChangePointsByTime
def test_bytime_append_keeps_time_order():
    c = ChangePointsByTime()
    c.append(make_group(1.0, metric="a"))
    c.append(make_group(2.0, metric="b"))
    assert [g.time for g in c] == [1.0, 2.0]
    assert len(c) == 2


def test_bytime_append_same_time_merges_metrics():
    c = ChangePointsByTime()
    c.append(make_group(1.0, metric="a"))
    c.append(make_group(1.0, metric="b"))
    assert len(c) == 1
    assert set(c[0].metrics()) == {"a", "b"}


def test_bytime_append_duplicate_metric_same_time_raises():
    c = ChangePointsByTime()
    c.append(make_group(1.0, metric="a"))
    with pytest.raises(KeyError):
        c.append(make_group(1.0, metric="a"))


def test_bytime_append_decreasing_time_raises():
    c = ChangePointsByTime()
    c.append(make_group(2.0, metric="a"))
    with pytest.raises(ValueError):
        c.append(make_group(1.0, metric="b"))


def test_bytime_constructor_sorts_and_validates():
    groups = [make_group(3.0, "a"), make_group(1.0, "b"), make_group(2.0, "c")]
    c = ChangePointsByTime.from_list(groups)
    assert [g.time for g in c] == [1.0, 2.0, 3.0]
    # a single group must now be wrapped in a list (no convenience unwrapping)
    with pytest.raises(TypeError):
        ChangePointsByTime.from_list(make_group(1.0))


def test_bytime_constructor_rejects_dict_and_non_group():
    with pytest.raises(TypeError):
        ChangePointsByTime.from_dict({"m": []})
    with pytest.raises(TypeError):
        ChangePointsByTime.from_list([object()])


def test_bytime_base():
    with pytest.raises(TypeError):
        ChangePointsByTime.from_list([object()])


def test_bytime_extend():
    c = ChangePointsByTime()
    c.extend([make_group(1.0, "a"), make_group(2.0, "b")])
    assert [g.time for g in c] == [1.0, 2.0]
    with pytest.raises(TypeError):
        c.extend("not a list")


def test_bytime_metrics_union():
    c = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    assert c.metrics() == {"a", "b"}


def test_bytime_at_timestamp_exact_and_tolerant():
    c = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    assert c.at_timestamp(2.0).time == 2.0
    # within tolerance
    assert c.at_timestamp(2.00005).time == 2.0
    with pytest.raises(LookupError):
        c.at_timestamp(99.0)


def test_bytime_at_commit():
    c = ChangePointsByTime.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "b", commit="c2")]
    )
    assert c.at_commit("c2").time == 2.0
    with pytest.raises(LookupError):
        c.at_commit("nope")

    with pytest.raises(TypeError):
        c.append("xxx")

    with pytest.raises(TypeError):
        c.extend("xxx")

    with pytest.raises(TypeError):
        c.extend(["a", "b"])


def test_bytime_append_out_of_order():
    c = ChangePointsByTime.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "a", commit="c2")]
    )
    assert c.at_commit("c2").time == 2.0
    with pytest.raises(TypeError):
        c.extend("nope")
    with pytest.raises(ValueError):
        c.extend([make_group(1.0, "a", commit="c1")])

    with pytest.raises(TypeError):
        c.append("xxx")

    with pytest.raises(TypeError):
        c.extend("xxx")

    with pytest.raises(TypeError):
        c.extend(["a", "b"])


def test_bytime_get_change_points_for_metric_sparse():
    # 'a' appears at t=1 and t=3, 'b' only at t=2 -> sparse columns
    c = ChangePointsByTime.from_list(
        [make_group(1.0, "a", index=1), make_group(2.0, "b", index=2), make_group(3.0, "a", index=3)]
    )
    a_points = c.get_change_points_for_metric("a")
    assert [cp.index for cp in a_points] == [1, 3]
    assert [cp.index for cp in c.get_change_points_for_metric("b")] == [2]


def test_bytime_pivot_and_items():
    c = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    pivoted = c.pivot()
    assert isinstance(pivoted, ChangePointsByMetric)
    assert pivoted.metrics() == {"a", "b"}
    assert {k for k, _ in c.items()} == {"a", "b"}
    c = ChangePointsByTime.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "b", commit="c2")]
    )


def test_bytime_copy_is_deep():
    c = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    clone = c.copy()
    assert isinstance(clone, ChangePointsByTime)
    assert len(clone) == 2
    clone[0].changes["a"].stats.mean_1 = -1.0
    assert c[0].changes["a"].stats.mean_1 != -1.0


# ChangePointsByMetric
def test_bymetric_dict_constructor_sorts_by_time():
    g1, g2 = make_group(1.0, "m"), make_group(2.0, "m")
    bm = ChangePointsByMetric.from_dict({"m": [g2, g1]})  # unsorted input
    assert isinstance(bm, ChangePointsByMetric)
    assert [g.time for g in bm._change_points["m"]] == [1.0, 2.0]


def test_bymetric_dict_constructor_rejects_non_group():
    with pytest.raises(TypeError):
        ChangePointsByMetric.from_dict({"m": [object()]})


def test_bymetric_dict_constructor_rejects_random():
    with pytest.raises(TypeError):
        ChangePointsByMetric.from_dict([{}, {}])
    with pytest.raises(ValueError):
        g1, g2 = make_group(1.0, "m"), make_group(2.0, "m")
        _ = ChangePointsByMetric.from_dict({"XXX": [g1, g2]})  # unsorted input


def test_from_dict_is_metric_keyed_and_returns_by_metric():
    # A dict is inherently keyed by metric, so from_dict() always builds a
    # ChangePointsByMetric -- even when called on the base ChangePoints class.
    result = ChangePoints.from_dict({"m": [make_group(1.0, "m")]})
    assert isinstance(result, ChangePointsByMetric)
    assert result.metrics() == {"m"}


def test_bymetric_list_constructor():
    bm = ChangePointsByMetric.from_list([make_group(1.0, "a"), make_group(2.0, "a"), make_group(2.0, "b")])
    # from_list() returns the class it is called on (asymmetric with from_dict)
    assert isinstance(bm, ChangePointsByMetric)
    assert bm.metrics() == {"a", "b"}
    assert [cp.index for cp in bm.get_change_points_for_metric("a")] == [3, 3]


def test_bymetric_append_and_len():
    bm = ChangePointsByMetric()
    bm.append(make_group(1.0, "a"))
    bm.append(make_group(2.0, "a"))
    bm.append(make_group(1.0, "b"))
    assert bm.metrics() == {"a", "b"}
    # len == longest column
    assert len(bm) == 2
    with pytest.raises(TypeError):
        bm.append("xxx")


def test_bymetric_select_metrics():
    bm = ChangePointsByMetric.from_list([make_group(1.0, "a"), make_group(1.0, "b")])
    only_a = bm.select_metrics("a")
    assert only_a.metrics() == {"a"}


def test_bymetric_items_and_iter():
    bm = ChangePointsByMetric.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    assert {k for k, _ in bm.items()} == {"a", "b"}
    # iterating yields ChangePointGroups (via pivot to time order)
    times = [g.time for g in bm]
    assert times == sorted(times)


def test_bymetric_by_time_roundtrip():
    by_time = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    bm = by_time.pivot()
    again = bm.by_time()
    assert isinstance(again, ChangePointsByTime)
    assert [g.time for g in again] == [1.0, 2.0]


def test_by_time_by_time_self():
    by_time = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    same = by_time.by_time()
    # Yes it's the same object, a no-op, not a copy. (Open to other opinions here)
    assert by_time == same
    assert by_time.at_timestamp(1.0) == same.at_timestamp(1.0)


def test_by_time_bm():
    by_time = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    same = by_time.by_metric()
    # Yes it's the same object, a no-op, not a copy. (Open to other opinions here)
    assert by_time != same
    assert by_time.at_timestamp(1.0) == same.at_timestamp(1.0)


def test_justcp_bm():
    by_time = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    same = by_time.by_metric()
    # Yes it's the same object, a no-op, not a copy. (Open to other opinions here)
    assert by_time != same
    assert by_time.at_timestamp(1.0) == same.at_timestamp(1.0)


def test_bm_bm_self():
    by_metric = ChangePointsByMetric.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    same = by_metric.by_metric()
    assert by_metric == same
    assert by_metric.metrics() == same.metrics()


def test_by_time_pivot_roundtrip():
    by_time = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    bm = by_time.pivot()
    again = bm.pivot()
    bm_again = again.pivot()
    assert isinstance(bm, ChangePointsByMetric)
    assert isinstance(again, ChangePointsByTime)
    assert isinstance(bm_again, ChangePointsByMetric)
    assert [g.time for g in again] == [1.0, 2.0]


def test_by_time_self():
    by_time = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "b")])
    same = by_time.by_time()
    # Yes it's the same object, a no-op, not a copy. (Open to other opinions here)
    assert by_time == same
    assert by_time.at_timestamp(1.0) == same.at_timestamp(1.0)


def test_bymetric_at_timestamp_and_at_commit():
    bm = ChangePointsByMetric.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "b", commit="c2")]
    )
    assert bm.at_timestamp(2.0).time == 2.0
    assert bm.at_commit("c1").time == 1.0


def test_bymetric_copy_is_deep():
    bm = ChangePointsByMetric.from_list([make_group(1.0, "a"), make_group(2.0, "a")])
    clone = bm.copy()
    assert isinstance(clone, ChangePointsByMetric)
    assert clone.metrics() == {"a"}
    clone._change_points["a"][0].changes["a"].stats.mean_1 = -1.0
    assert bm._change_points["a"][0].changes["a"].stats.mean_1 != -1.0


def test_bymetric__setitem_in():
    bm = ChangePointsByMetric.from_list([make_group(1.0, "a"), make_group(2.0, "a")])
    bm["x"] = make_group(99.9, metric="x", index=55)
    assert "x" in bm._change_points
    assert bm._change_points["x"].time == 99.9
    assert bm._change_points["x"].changes["x"].index == 55


def test_bymetric_at_commit():
    c = ChangePointsByMetric.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "a", commit="c2")]
    )
    assert c.at_commit("c2").time == 2.0
    with pytest.raises(LookupError):
        c.at_commit("nope")

    with pytest.raises(TypeError):
        c.append("xxx")

    with pytest.raises(TypeError):
        c.extend(["a", "b"])


def test_bymetric_append_out_of_order():
    c = ChangePointsByMetric.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "a", commit="c2")]
    )
    with pytest.raises(TypeError):
        c.extend("nope")
    with pytest.raises(ValueError):
        c.extend([make_group(1.1, "a", commit="c11")])

    with pytest.raises(TypeError):
        c.append("xxx")

    with pytest.raises(TypeError):
        c.extend("xxx")

    with pytest.raises(TypeError):
        c.extend(["a", "b"])


def test_cpbm_getitem():
    _ = ChangePointsByMetric.from_list(
        [make_group(1.0, "a", commit="c1"), make_group(2.0, "a", commit="c2")]
    )


def test_cpbm_append():
    cpbm = ChangePointsByMetric()
    cpg = make_group(3.0, "b")
    cpbm.append(cpg)

    cpg = make_group(1.0, "a")
    cpbm.append(cpg)

    cpg = make_group(2.0, "a")
    cpbm.append(cpg)

    with pytest.raises(ValueError):
        cpg = make_group(1.1, "a")
        cpbm.append(cpg)

    with pytest.raises(ValueError):
        cpg = make_group(3.0, "b")
        cpg.changes["b"].metric = "boo"
        cpbm.append(cpg)


def test_cpbm_extend():
    cpbm = ChangePointsByMetric()
    cpg = make_group(3.0, "b")
    cpbm.extend([cpg])

    cpg = make_group(1.0, "a")
    cpbm.extend([cpg])

    cpg = make_group(2.0, "a")
    cpbm.extend([cpg])

    with pytest.raises(ValueError):
        cpg = make_group(1.1, "a")
        cpbm.extend([cpg])

    with pytest.raises(ValueError):
        cpg = make_group(3.0, "b")
        cpg.changes["b"].metric = "boo"
        cpbm.extend([cpg])


def test_contains():
    cpbm = ChangePointsByMetric()
    cpg = make_group(1.0, "a")
    cpbm.extend([cpg])
    assert "a" in cpbm._change_points
    assert "b" not in cpbm._change_points
    assert "a" in cpbm
    assert "b" not in cpbm
    assert "a" in cpbm.keys()
    assert "b" not in cpbm.keys()
    assert "a" in cpbm.metrics()
    assert "b" not in cpbm.metrics()

    cpbt = ChangePoints()
    cpg = make_group(9.0, "x")
    cpbt.extend([cpg])
    assert "x" in cpbt
    assert "y" not in cpbt
    assert "x" in cpbt.metrics()
    assert "y" not in cpbt.metrics()


def test_len():
    cpbm = ChangePointsByMetric.from_list([make_group(1, "a"), make_group(2, "a")])
    assert len(cpbm) == 2


def test_inconsistent_metric():
    cpbm = ChangePointsByMetric()
    cpg = make_group(1.0, "a")
    cpbm.append(cpg)
    cpg = make_group(2.0, "a")
    cpbm.extend([cpg])
    with pytest.raises(ValueError):
        cpg = make_group(3.0, "a")
        cpg.changes["a"].metric = "foo"
        cpbm.append(cpg)
    with pytest.raises(ValueError):
        cpg = make_group(4.0, "a")
        cpg.changes["a"].metric = "foo"
        cpbm.extend([cpg])
    with pytest.raises(ValueError):
        cpbm._change_points["a"][0].changes["a"].metric = "foo"
        _ = cpbm.get_change_points_for_metric("a")


def test_inconsistent_metric_by_time():
    cpbt = ChangePointsByTime.from_list([make_group(1.0, "a"), make_group(2.0, "a")])
    with pytest.raises(ValueError):
        cpbt._change_points[0].changes["a"].metric = "foo"
        _ = cpbt.get_change_points_for_metric("a")


def test_select_metrics():
    cpbm = ChangePointsByMetric.from_list([make_group(1, "a"), make_group(2, "b")])

    metrics = cpbm.select_metrics("a")
    assert "a" in metrics
    assert "b" not in metrics

    metrics = cpbm.select_metrics("b")
    assert "b" in metrics
    assert "a" not in metrics

    metrics = cpbm.select_metrics(["a", "b"])
    assert "a" in metrics
    assert "b" in metrics

    with pytest.raises(KeyError):
        metrics = cpbm.select_metrics(["a", "b", "c"])

    with pytest.raises(KeyError):
        metrics = cpbm.select_metrics("c")

    with pytest.raises(TypeError):
        metrics = cpbm.select_metrics({})


# SignificanceTester helpers
def test_tester_compare_returns_basestats():
    tester = SignificanceTester(0.05)
    stats = tester.compare([1.0, 1.0], [5.0, 5.0], 0.01)
    assert isinstance(stats, BaseStats)
    assert stats.mean_1 == 1.0
    assert stats.mean_2 == 5.0
    assert stats.pvalue == 0.01


def test_tester_compare_empty_raises():
    tester = SignificanceTester(0.05)
    with pytest.raises(ValueError):
        tester.compare([], [1.0])


def test_tester_get_intervals():
    tester = SignificanceTester(0.05)
    intervals = tester.get_intervals([make_cp(index=3)])
    assert intervals == [slice(0, 3), slice(3, None)]


def test_tester_get_sides_split_step():
    tester = SignificanceTester(0.05)
    series = np.array([1.0, 1.0, 1.0, 5.0, 5.0, 5.0])
    intervals = tester.get_intervals([make_cp(index=3)])
    left, right = tester.get_sides(CandidateChangePoint(index=3, qhat=1.0), series, intervals)
    assert list(left) == [1.0, 1.0, 1.0]
    assert list(right) == [5.0, 5.0, 5.0]


def test_tester_get_sides_merge_step():
    tester = SignificanceTester(0.05)
    series = np.arange(9, dtype=float)
    intervals = [slice(0, 3), slice(3, 6), slice(6, None)]
    # candidate index matches the stop of the first interval -> merge step
    left, right = tester.get_sides(CandidateChangePoint(index=3, qhat=1.0), series, intervals)
    assert list(left) == [0.0, 1.0, 2.0]
    assert list(right) == [3.0, 4.0, 5.0]


def test_tester_get_sides_not_exist():
    tester = SignificanceTester(0.05)
    series = np.arange(9, dtype=float)
    intervals = [slice(0, 3), slice(3, 6), slice(6, None)]
    # candidate index matches the stop of the first interval -> merge step
    with pytest.raises(ValueError):
        left, right = tester.get_sides(CandidateChangePoint(index=-1, qhat=1.0), series, intervals)


def test_tester_is_significant():
    tester = SignificanceTester(0.05)
    assert tester.is_significant(make_cp(pvalue=0.01)) is True
    assert tester.is_significant(make_cp(pvalue=0.5)) is False


# Base ChangePoints behaviours shared by both representations
def test_base_changepoints_empty():
    c = ChangePoints()
    assert len(c) == 0
    assert list(c) == []
