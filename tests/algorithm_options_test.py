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

import configargparse
import pytest
from pydantic import ValidationError

from otava import serialization
from otava.main import (
    analysis_options_from_args,
    script_main,
    setup_analysis_options_parser,
)
from otava.serialization import AnalysisOptionsModel
from otava.series import AnalysisOptions, AnalyzedSeries, Metric, Series

SUPPORTED_PAIRS = [("t-test", "split-merge"), ("t-test", "whole-series"), ("permutation", "whole-series")]


@pytest.mark.parametrize("model", [AnalysisOptionsModel, AnalysisOptions])
def test_default_options_use_ttest_with_split_merge(model):
    """Default to t-test significance and split/merge segmentation."""
    options = model()

    assert options.significance_test is serialization.SignificanceTest.T_TEST
    assert options.segmentation is serialization.Segmentation.SPLIT_MERGE


@pytest.mark.parametrize("test,segmentation", SUPPORTED_PAIRS)
def test_supported_options_normalize_and_round_trip(test, segmentation):
    """Persist and restore the two independently selected options as enums."""
    options = AnalysisOptions(significance_test=test, segmentation=segmentation)

    assert options.significance_test is serialization.SignificanceTest(test)
    assert options.segmentation is serialization.Segmentation(segmentation)
    assert options.model_dump(mode="json") == {
        "window_len": 50, "max_pvalue": .001, "min_magnitude": 0.,
        "significance_test": test, "segmentation": segmentation,
    }
    restored = AnalysisOptions.model_validate_json(options.model_dump_json())
    assert restored == options


@pytest.mark.parametrize("field", ["significance_test", "segmentation"])
@pytest.mark.parametrize("value", ["unknown", "", None, True, 1, ["t-test", "permutation"]])
def test_invalid_option_values_are_rejected(field, value):
    """Reject unknown or ambiguous test and segmentation values."""
    with pytest.raises(ValidationError):
        AnalysisOptions(**{field: value})


@pytest.mark.parametrize("field", ["orig_edivisive", "deterministic_edivisive", "split_edivisive", "algorithm"])
def test_variant_selection_fields_are_rejected(field):
    """Require significance and segmentation options rather than named variants."""
    with pytest.raises(ValidationError):
        AnalysisOptions(**{field: True})


@pytest.mark.parametrize("values", [
    {"significance_test": "permutation"},
    {"significance_test": "permutation", "segmentation": "split-merge"},
])
def test_permutation_split_merge_is_not_supported(values):
    """Reject permutation tests with explicit or default split/merge segmentation."""
    with pytest.raises(ValidationError, match="not supported"):
        AnalysisOptions(**values)


@pytest.mark.parametrize("initial,field,value", [
    ({}, "significance_test", "permutation"),
    ({"significance_test": "permutation", "segmentation": "whole-series"}, "segmentation", "split-merge"),
    ({}, "significance_test", "unknown"),
    ({}, "segmentation", "unknown"),
])
def test_invalid_assignment_leaves_options_unchanged(initial, field, value):
    """Reject invalid assignments without leaving an unsupported pair in the model."""
    options = AnalysisOptions(**initial)
    before = options.model_dump()

    with pytest.raises(ValidationError):
        setattr(options, field, value)

    assert options.model_dump() == before


def test_options_can_transition_between_supported_pairs():
    """Change segmentation before selecting permutation, and restore t-test first."""
    options = AnalysisOptions()
    options.segmentation = "whole-series"
    options.significance_test = "permutation"
    assert options.significance_test is serialization.SignificanceTest.PERMUTATION
    assert options.segmentation is serialization.Segmentation.WHOLE_SERIES

    options.significance_test = "t-test"
    options.segmentation = "split-merge"
    assert options.significance_test is serialization.SignificanceTest.T_TEST
    assert options.segmentation is serialization.Segmentation.SPLIT_MERGE


@pytest.mark.parametrize("test,segmentation", SUPPORTED_PAIRS)
def test_saved_analysis_preserves_both_options(test, segmentation):
    """Store both selections in analyzed-series JSON and restore their enum values."""
    values = [1.] * 20 + [5.] * 20
    analyzed = Series(
        "algorithm", branch=None, time=list(range(40)), metrics={"latency": Metric()},
        data={"latency": values}, attributes={},
    ).analyze(AnalysisOptions(significance_test=test, segmentation=segmentation))

    payload = analyzed.to_json()
    restored = AnalyzedSeries.from_json(payload)

    assert payload["options"] == {
        "window_len": 50, "max_pvalue": .001, "min_magnitude": 0.,
        "significance_test": test, "segmentation": segmentation,
    }
    assert restored.options.significance_test is serialization.SignificanceTest(test)
    assert restored.options.segmentation is serialization.Segmentation(segmentation)
    assert restored.to_json()["options"] == payload["options"]


@pytest.mark.parametrize("values", [
    {"significance_test": "unknown"},
    {"segmentation": "unknown"},
    {"significance_test": "permutation", "segmentation": "split-merge"},
])
def test_saved_analysis_rejects_invalid_options(values):
    """Reject invalid values and unsupported pairs when loading saved analyses."""
    analyzed = Series(
        "algorithm", branch=None, time=[0, 1], metrics={"latency": Metric()},
        data={"latency": [1., 1.]}, attributes={},
    ).analyze()
    payload = analyzed.to_json()
    payload["options"].update(values)

    with pytest.raises(ValidationError):
        AnalyzedSeries.from_json(payload)


@pytest.mark.parametrize("flags,test,segmentation", [
    ([], "t-test", "split-merge"),
    (["--segmentation", "whole-series"], "t-test", "whole-series"),
    (["--significance-test", "permutation", "--segmentation", "whole-series"], "permutation", "whole-series"),
    (["--significance-test", "t-test", "--segmentation", "split-merge"], "t-test", "split-merge"),
])
def test_cli_selects_significance_and_segmentation(flags, test, segmentation):
    """Map each supported CLI pair to the corresponding validated enum fields."""
    parser = configargparse.ArgumentParser()
    setup_analysis_options_parser(parser)

    options = analysis_options_from_args(parser.parse_args(flags))

    assert options.significance_test is serialization.SignificanceTest(test)
    assert options.segmentation is serialization.Segmentation(segmentation)


@pytest.mark.parametrize("flags", [
    ["--significance-test", "unknown"], ["--segmentation", "unknown"],
    ["--split-edivisive"], ["--deterministic-edivisive"], ["--orig-edivisive"],
])
def test_cli_rejects_invalid_options_and_variant_flags(flags):
    """Accept only the two canonical option names and their known choices."""
    parser = configargparse.ArgumentParser()
    setup_analysis_options_parser(parser)

    with pytest.raises(SystemExit) as error:
        parser.parse_args(flags)

    assert error.value.code == 2


@pytest.mark.parametrize("flags", [
    ["--significance-test", "permutation"],
    ["--significance-test", "permutation", "--segmentation", "split-merge"],
])
def test_cli_reports_unsupported_pair_as_usage_error(flags, capsys):
    """Report unsupported pairs as CLI errors before loading tests or services."""
    with pytest.raises(SystemExit) as error:
        script_main(args=["analyze", *flags, "unused-test"])

    assert error.value.code == 2
    assert "not supported" in capsys.readouterr().err


@pytest.mark.parametrize("values", [
    {"significance_test": "permutation", "segmentation": "split-merge"},
    {"significance_test": "unknown", "segmentation": "whole-series"},
    {"significance_test": "t-test", "segmentation": "unknown"},
])
def test_dispatch_rejects_unvalidated_pairs(values):
    """Bypassing model validation cannot silently select a different algorithm."""
    options = AnalysisOptions.model_construct(**values)
    analyzed = Series(
        "algorithm", branch=None, time=[0, 1], metrics={"latency": Metric()},
        data={"latency": [1., 1.]}, attributes={},
    ).analyze(options)

    with pytest.raises(ValueError, match="not supported"):
        _ = analyzed.change_points
