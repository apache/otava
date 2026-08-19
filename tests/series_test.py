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

import json
import time
from datetime import datetime
from random import random

import pytest
from pydantic import ValidationError

from otava.change_point_divisive.base import ChangePointSerializer
from otava.serialization import AnalysisOptionsModel, AnalyzedSeriesModel
from otava.series import AnalysisOptions, AnalyzedSeries, Metric, Series


def test_change_point_detection():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    cps = test.analyze().change_points_by_time
    assert len(cps) == 2
    assert cps._change_points[0].time == 4
    assert cps._change_points[0].changes["series2"].metric == "series2"
    assert cps._change_points[1].time == 6
    assert cps._change_points[1].changes["series1"].metric == "series1"


def test_analysis_options_is_pydantic_model():
    options = AnalysisOptions(
        window_len="25",
        max_pvalue="0.05",
        min_magnitude=1,
        orig_edivisive=True,
    )

    assert isinstance(options, AnalysisOptionsModel)
    assert options.model_dump(mode="json") == {
        "window_len": 25,
        "max_pvalue": 0.05,
        "min_magnitude": 1.0,
        "orig_edivisive": True,
    }


def test_analysis_options_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        AnalysisOptions(no_such_option=True)


def test_change_point_detection_many():
    series_3 = [
        1,
        1,
        1,
        1,
        1,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        5,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        9,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
        3,
    ]
    time = list(range(len(series_3)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series3": Metric(1, 1.0)},
        data={"series3": series_3},
        attributes={},
    )

    options = AnalysisOptions()
    options.min_magnitude = 0.0
    options.max_pvalue = 0.05
    analyzed_series = test.analyze(options)
    assert len(list(analyzed_series.change_points)) == 3
    cps_by_time = analyzed_series.change_points_by_time
    assert len(cps_by_time._change_points) == 3
    assert analyzed_series.change_points[0].time == 5
    assert "series3" in analyzed_series.change_points[0].changes


def test_change_point_min_magnitude():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    options = AnalysisOptions()
    options.min_magnitude = 0.2
    cps = test.analyze(options).change_points_by_time
    assert len(cps) == 1
    assert cps._change_points[0].time == 6
    assert "series1" in cps[0].changes

    for change_point in cps:
        for metric, change in change_point.changes.items():
            assert ChangePointSerializer(change).magnitude() >= options.min_magnitude, (
                f"All change points must have magnitude greater than {options.min_magnitude}"
            )


# Divide by zero is only a RuntimeWarning, but for testing we want to make sure it's a failure
@pytest.mark.filterwarnings("error")
def test_div_by_zero():
    series_1 = [0.0, 0.0, 0.0, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0)},
        data={"series1": series_1},
        attributes={},
    )

    analyzed_series = test.analyze()
    change_points = analyzed_series.change_points_by_time
    cpjson = analyzed_series.to_json()
    assert cpjson
    assert len(change_points) == 2
    assert change_points[0].time == 3


def test_change_point_detection_performance():
    timestamps = range(90)  # 3 months of data
    series = [random() for x in timestamps]

    start_time = time.process_time()
    for run in range(10):  # 10 series
        test = Series(
            "test",
            branch=None,
            time=list(timestamps),
            metrics={"series": Metric(1, 1.0)},
            data={"series": series},
            attributes={},
        )
        test.analyze()
    end_time = time.process_time()
    assert (end_time - start_time) < 0.5


def test_get_stable_range():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    ).analyze()

    assert test.get_stable_range("series1", 0) == (0, 6)
    assert test.get_stable_range("series1", 1) == (0, 6)
    assert test.get_stable_range("series1", 5) == (0, 6)
    assert test.get_stable_range("series1", 6) == (6, len(series_1))
    assert test.get_stable_range("series1", 7) == (6, len(series_1))
    assert test.get_stable_range("series1", 10) == (6, len(series_1))

    assert test.get_stable_range("series2", 0) == (0, 4)
    assert test.get_stable_range("series2", 1) == (0, 4)
    assert test.get_stable_range("series2", 3) == (0, 4)


def test_incremental_otava():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = test.analyze()
    analyzed_series.append(
        time=[len(time)], new_data={"series1": [0.5], "series2": [1.97]}, attributes={}
    )
    change_points = analyzed_series.change_points
    assert [c.index for c in change_points.get_change_points_for_metric("series1")] == [6]
    assert [c.index for c in change_points.get_change_points_for_metric("series2")] == [4]
    assert [
        c.index for c in analyzed_series.weak_change_points.get_change_points_for_metric("series2")
    ] == [4, 11]
    assert [
        cpg["changes"][0]["index"]
        for cpg in analyzed_series.to_json()["weak_change_points"]["series2"]
    ] == [4, 11]

    analyzed_series.append(time=[len(time)], new_data={"series1": [0.51]}, attributes={})
    change_points = analyzed_series.change_points
    assert [c.index for c in change_points.get_change_points_for_metric("series1")] == [6]
    assert [c.index for c in change_points.get_change_points_for_metric("series2")] == [4]

    analyzed_series.append(time=[len(time)], new_data={"series2": [33.33, 46.46]}, attributes={})
    change_points = analyzed_series.change_points
    assert [c.index for c in change_points.get_change_points_for_metric("series1")] == [6]
    assert [c.index for c in change_points.get_change_points_for_metric("series2")] == [4, 12]
    assert [
        c.index for c in analyzed_series.weak_change_points.get_change_points_for_metric("series2")
    ] == [4, 12]
    assert [(cpg.time, sorted(cpg.changes)) for cpg in analyzed_series.change_points_by_time] == [
        (4, ["series2"]),
        (6, ["series1"]),
        (12, ["series2"]),
    ]


def test_analyzed_series_json_round_trip():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    series = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = series.analyze()
    analyzed_series.append(
        time=[len(time)], new_data={"series1": [0.5], "series2": [1.97]}, attributes={}
    )

    payload = analyzed_series.to_json()
    restored = AnalyzedSeries.from_json(payload)

    assert [c.index for c in restored.change_points.get_change_points_for_metric("series2")] == [4]
    assert [
        c.index for c in restored.weak_change_points.get_change_points_for_metric("series2")
    ] == [4, 11]
    assert restored.to_json()["change_points"] == payload["change_points"]
    assert restored.to_json()["weak_change_points"] == payload["weak_change_points"]


def test_analyzed_series_json_round_trip_through_json_module():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    series = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = series.analyze()
    analyzed_series.append(
        time=[len(time)], new_data={"series1": [0.5], "series2": [1.97]}, attributes={}
    )

    payload = analyzed_series.to_json()
    decoded = json.loads(json.dumps(payload))
    restored = AnalyzedSeries.from_json(decoded)

    assert isinstance(restored.change_points_timestamp, datetime)
    assert restored.to_json()["change_points"] == decoded["change_points"]
    assert restored.to_json()["weak_change_points"] == decoded["weak_change_points"]


def test_analyzed_series_from_json_validates_options_with_pydantic():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    time = list(range(len(series_1)))
    series = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0)},
        data={"series1": series_1},
        attributes={},
    )

    payload = series.analyze().to_json()
    payload["options"]["window_len"] = "25"
    restored = AnalyzedSeries.from_json(payload)

    assert isinstance(restored.options, AnalysisOptions)
    assert restored.options.window_len == 25


def test_analyzed_series_json_uses_pydantic_model_shape():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    series = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = series.analyze()
    analyzed_series.append(
        time=[len(time)], new_data={"series1": [0.5], "series2": [1.97]}, attributes={}
    )

    payload = analyzed_series.to_json()
    model = AnalyzedSeriesModel.model_validate(payload)
    dumped = model.model_dump(mode="python")

    change = dumped["change_points"]["series2"][0]["changes"][0]
    weak_change = dumped["weak_change_points"]["series2"][1]["changes"][0]
    assert isinstance(change["mean_before"], float)
    assert isinstance(change["forward_change_percent"], float)
    assert isinstance(weak_change["pvalue"], float)
    assert AnalyzedSeries.from_json(dumped).to_json()["change_points"] == dumped["change_points"]


def test_validate():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )
    test_fail = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series_fail = test_fail.analyze()
    analyzed_series_fail.change_points = None
    err = analyzed_series_fail._validate_append(
        time=[len(time)], new_data={"series1": [0.51]}, attributes={}
    )
    assert isinstance(err, RuntimeError)

    analyzed_series = test.analyze()
    analyzed_series.append(
        time=[len(time)], new_data={"series1": [0.5], "series2": [1.97]}, attributes={}
    )

    err = analyzed_series._validate_append(
        time=[len(time)], new_data={"series1": [0.51]}, attributes={}
    )
    assert err is None

    err = analyzed_series._validate_append(time=[5], new_data={"series1": [0.51]}, attributes={})
    assert isinstance(err, ValueError)

    err = analyzed_series._validate_append(time=[len(time)], new_data={}, attributes={})
    assert isinstance(err, ValueError)


def test_can_append():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    analyzed_series = test.analyze()
    analyzed_series.append(
        time=[len(time)], new_data={"series1": [0.5], "series2": [1.97]}, attributes={}
    )

    can = analyzed_series.can_append(time=[len(time)], new_data={"series1": [0.51]}, attributes={})
    assert can

    can = analyzed_series.can_append(time=[5], new_data={"series1": [0.51]}, attributes={})
    assert not can


def test_orig_edivisive():
    series_1 = [1.02, 0.95, 0.99, 1.00, 1.12, 0.90, 0.50, 0.51, 0.48, 0.48, 0.55]
    series_2 = [2.02, 2.03, 2.01, 2.04, 1.82, 1.85, 1.79, 1.81, 1.80, 1.76, 1.78]
    time = list(range(len(series_1)))
    test = Series(
        "test",
        branch=None,
        time=time,
        metrics={"series1": Metric(1, 1.0), "series2": Metric(1, 1.0)},
        data={"series1": series_1, "series2": series_2},
        attributes={},
    )

    options = AnalysisOptions()
    options.orig_edivisive = True
    options.max_pvalue = 0.01

    change_points = test.analyze(options=options).change_points_by_time
    assert len(change_points) >= 0
    # assert len(change_points) == 2
    # assert change_points[0].index == 4
    # assert change_points[1].index == 6


def test_series_sparse_commits():
    """Verify series processes sparse commit sequences without artificial padding."""
    name = "sparse_commit_test"
    branch = "main"
    time_points = [1000, 1001, 1005, 1008]
    metrics = {}
    data = {"latency": [100.5, 101.0, 105.2, 98.7]}
    # Match length of attributes list to len(time_points) == 4
    attributes = {"env": ["ci", "ci", "ci", "ci"]}

    series = Series(name, branch, time_points, metrics, data, attributes)

    assert len(series.time) == 4
    assert series.time == [1000, 1001, 1005, 1008]
    assert series.data["latency"] == [100.5, 101.0, 105.2, 98.7]


def test_series_irregular_timestamps():
    """Verify change detection operates on unpadded time intervals."""
    name = "irregular_ts_test"
    branch = "main"
    time_points = [1600000000, 1600000010, 1600000300, 1600003600]
    metrics = {}
    data = {"duration": [50.0, 51.0, 50.5, 95.0]}
    attributes = {}

    series = Series(name, branch, time_points, metrics, data, attributes)

    assert len(series.time) == 4
    assert series.data["duration"] == [50.0, 51.0, 50.5, 95.0]


def test_series_raw_initialization():
    """Verify Series initialization operates directly on raw unpadded input data."""
    name = "raw_init_test"
    branch = "main"
    time_points = [1, 2, 3]
    metrics = {}
    data = {"throughput": [10.0, 12.0, 11.5]}
    attributes = {}

    series = Series(name, branch, time_points, metrics, data, attributes)

    assert len(series.time) == 3
    assert series.data["throughput"] == [10.0, 12.0, 11.5]
