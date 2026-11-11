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

from functools import partial

import pytest

from otava import series as series_module
from otava.change_point_divisive.significance_test import PermutationStats
from otava.series import AnalysisOptions, AnalyzedSeries, Metric, Series
from tests.tigerbeetle_test import tigerbeetle_demo_data


def analysis_options(mode, monkeypatch):
    if mode == "orig":
        # Exercise the real permutation detector with reproducible draws.
        monkeypatch.setattr(
            series_module, "compute_change_points_orig",
            partial(series_module.compute_change_points_orig, seed=1),
        )
    return AnalysisOptions(
        significance_test="permutation" if mode == "orig" else "t-test",
        segmentation="split-merge" if mode == "split" else "whole-series",
        window_len=30,
    )


def make_series(data):
    return Series(
        "append_test", branch=None,
        time=list(range(len(next(iter(data.values()))))),
        metrics={metric: Metric() for metric in data},
        data={metric: values.copy() for metric, values in data.items()},
        attributes={},
    )


def metric_snapshot(points, metric):
    if metric not in points:
        return []
    return [group.to_json() for group in points.select_metrics(metric)]


@pytest.mark.parametrize("mode", ["split", "deterministic", "orig"])
@pytest.mark.parametrize("initial_state", ["lazy", "cached", "restored"])
@pytest.mark.parametrize("tail,expected_indexes", [([5.] * 5, [20]), ([9.] * 12, [20, 40])])
def test_append_matches_fresh_analysis(mode, initial_state, tail, expected_indexes, monkeypatch):
    """Compare append with fresh analysis for every algorithm and cache state.

    Append either more of the final value or values introducing another change.
    Compare statistics and weak points as well as change-point indexes.
    """
    options = analysis_options(mode, monkeypatch)
    initial = [1.] * 20 + [5.] * 20
    analyzed = make_series({"latency": initial}).analyze(options)
    if initial_state == "cached":
        assert [group.time for group in analyzed.change_points_by_time] == [20]
    elif initial_state == "restored":
        analyzed = AnalyzedSeries.from_json(analyzed.to_json())

    updated, weak = analyzed.append(
        list(range(40, 40 + len(tail))), {"latency": tail}, {}
    )
    fresh = make_series({"latency": initial + tail}).analyze(options)

    assert [point.index for point in fresh.change_points.get_change_points_for_metric("latency")] == expected_indexes
    assert metric_snapshot(updated, "latency") == metric_snapshot(fresh.change_points, "latency")
    assert metric_snapshot(analyzed.change_points, "latency") == metric_snapshot(fresh.change_points, "latency")
    assert metric_snapshot(weak, "latency") == metric_snapshot(fresh.weak_change_points, "latency")
    assert metric_snapshot(analyzed.weak_change_points, "latency") == metric_snapshot(fresh.weak_change_points, "latency")
    assert [group.time for group in analyzed.change_points_by_time] == expected_indexes
    assert analyzed.data("latency") == initial + tail
    if mode == "orig":
        assert all(isinstance(point.stats, PermutationStats) for point in updated.get_change_points_for_metric("latency"))


@pytest.mark.parametrize("mode,expected_indexes", [
    ("deterministic", [10, 11, 15, 61, 71, 95, 117, 131, 142, 148, 192, 212, 260, 363, 364]),
    ("orig", [15, 71, 95, 131, 192]),
])
def test_append_unchanged_tigerbeetle_tail_keeps_selected_algorithm(mode, expected_indexes, monkeypatch):
    """Ensure append preserves the selected algorithm after an unchanged sample.

    Original and deterministic modes must match fresh analysis without weak points.
    """
    options = analysis_options(mode, monkeypatch)
    initial = tigerbeetle_demo_data()
    analyzed = make_series({"latency": initial}).analyze(options)
    _ = analyzed.change_points_by_time

    analyzed.append([len(initial)], {"latency": [initial[-1]]}, {})
    fresh = make_series({"latency": initial + [initial[-1]]}).analyze(options)

    assert [point.index for point in analyzed.change_points.get_change_points_for_metric("latency")] == expected_indexes
    assert metric_snapshot(analyzed.change_points, "latency") == metric_snapshot(fresh.change_points, "latency")
    assert not list(analyzed.weak_change_points)


@pytest.mark.parametrize("mode", ["split", "deterministic", "orig"])
def test_append_subset_preserves_untouched_metric_results(mode, monkeypatch):
    """Preserve untouched data and strong/weak points across two subset updates.

    Also check that the timestamp and cached by-time view reflect the updates.
    """
    options = analysis_options(mode, monkeypatch)
    initial = [1.] * 20 + [5.] * 20
    analyzed = make_series({"updated": initial, "untouched": initial}).analyze(options)
    old_points = metric_snapshot(analyzed.change_points, "untouched")
    old_weak = metric_snapshot(analyzed.weak_change_points, "untouched")
    _ = analyzed.change_points_by_time
    before_timestamp = analyzed.change_points_timestamp

    for start, value in [(40, 9.), (52, 20.)]:
        updated, _ = analyzed.append(list(range(start, start + 12)), {"updated": [value] * 12}, {})
        assert "untouched" not in updated
        assert metric_snapshot(analyzed.change_points, "untouched") == old_points
        assert metric_snapshot(analyzed.weak_change_points, "untouched") == old_weak
        assert analyzed.data("untouched") == initial
    assert analyzed.change_points_timestamp > before_timestamp
    assert [point.index for point in analyzed.change_points.get_change_points_for_metric("updated")] == [20, 40, 52]
    assert [group.time for group in analyzed.change_points_by_time] == [20, 40, 52]


def test_deterministic_append_clears_points_when_full_analysis_finds_none():
    """Clear stale cached points and views when full recomputation finds no changes."""
    initial = [1.] * 10 + [5.] * 10
    options = AnalysisOptions(segmentation="whole-series")
    analyzed = make_series({"latency": initial}).analyze(options)
    assert [group.time for group in analyzed.change_points_by_time] == [10]
    tail = [1000., -1000.] * 10

    updated, weak = analyzed.append(list(range(20, 40)), {"latency": tail}, {})

    assert metric_snapshot(updated, "latency") == []
    assert metric_snapshot(analyzed.change_points, "latency") == []
    assert not list(analyzed.change_points_by_time)
    assert not list(weak)
    assert not list(analyzed.weak_change_points)


@pytest.mark.parametrize("mode", ["split", "deterministic", "orig"])
def test_append_detects_first_change_after_stable_history(mode, monkeypatch):
    """Detect an appended shift even when the initial cached result was empty."""
    options = analysis_options(mode, monkeypatch)
    analyzed = make_series({"latency": [1.] * 20}).analyze(options)
    assert not list(analyzed.change_points)

    analyzed.append(list(range(20, 40)), {"latency": [5.] * 20}, {})

    assert [point.index for point in analyzed.change_points.get_change_points_for_metric("latency")] == [20]


def test_deterministic_append_respects_magnitude_threshold():
    """Keep the existing large shift while filtering a smaller appended shift."""
    options = AnalysisOptions(segmentation="whole-series", min_magnitude=1.)
    analyzed = make_series({"latency": [1.] * 20 + [5.] * 20}).analyze(options)
    assert [group.time for group in analyzed.change_points_by_time] == [20]

    # The new 5 -> 9 shift is below the configured relative-magnitude threshold.
    analyzed.append(list(range(40, 52)), {"latency": [9.] * 12}, {})

    assert [point.index for point in analyzed.change_points.get_change_points_for_metric("latency")] == [20]
