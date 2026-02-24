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

from datetime import datetime

import pytest
import pytz

from otava.csv_options import CsvOptions
from otava.graphite import DataSelector
from otava.importer import (
    BigQueryImporter,
    CsvImporter,
    DataImportError,
    HistoStatImporter,
    PostgresImporter,
)
from otava.test_config import (
    BigQueryMetric,
    BigQueryTestConfig,
    CsvMetric,
    CsvTestConfig,
    GraphiteMetric,
    GraphiteTestConfig,
    HistoStatTestConfig,
    PostgresMetric,
    PostgresTestConfig,
    TestConfigError,
)

SAMPLE_CSV = "tests/resources/sample.csv"


def csv_test_config(file, csv_options=None):
    return CsvTestConfig(
        name="test",
        file=file,
        csv_options=csv_options if csv_options else CsvOptions(),
        time_column="time",
        metrics=[CsvMetric("m1", 1, 1.0, "metric1"), CsvMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )


def data_selector():
    selector = DataSelector()
    selector.since_time = datetime(1970, 1, 1, 1, 1, 1, tzinfo=pytz.UTC)
    return selector


def test_import_csv():
    test = csv_test_config(SAMPLE_CSV)
    importer = CsvImporter()
    series = importer.fetch_data(test_conf=test, selector=data_selector())
    assert len(series.data.keys()) == 2
    assert len(series.time) == 10
    assert len(series.data["m1"]) == 10
    assert len(series.data["m2"]) == 10
    assert len(series.attributes["commit"]) == 10


def test_import_csv_with_metrics_filter():
    test = csv_test_config(SAMPLE_CSV)
    importer = CsvImporter()
    selector = data_selector()
    selector.metrics = ["m2"]
    series = importer.fetch_data(test, selector=selector)
    assert len(series.data.keys()) == 1
    assert len(series.time) == 10
    assert len(series.data["m2"]) == 10
    assert series.metrics["m2"].scale == 5.0


def test_import_csv_with_time_filter():
    test = csv_test_config(SAMPLE_CSV)
    importer = CsvImporter()
    selector = data_selector()
    tz = pytz.timezone("Etc/GMT+1")
    selector.since_time = datetime(2024, 1, 5, 0, 0, 0, tzinfo=tz)
    selector.until_time = datetime(2024, 1, 7, 0, 0, 0, tzinfo=tz)
    series = importer.fetch_data(test, selector=selector)
    assert len(series.data.keys()) == 2
    assert len(series.time) == 2
    assert len(series.data["m1"]) == 2
    assert len(series.data["m2"]) == 2


def test_import_csv_with_unix_timestamps():
    test = csv_test_config(SAMPLE_CSV)
    importer = CsvImporter()
    series = importer.fetch_data(test_conf=test, selector=data_selector())
    assert len(series.data.keys()) == 2
    assert len(series.time) == 10
    assert len(series.data["m1"]) == 10
    assert len(series.data["m2"]) == 10
    ts = datetime(2024, 1, 1, 2, 0, 0, tzinfo=pytz.UTC).timestamp()
    assert series.time[0] == ts


def test_import_csv_semicolon_sep():
    options = CsvOptions()
    options.delimiter = ";"
    test = csv_test_config("tests/resources/sample-semicolons.csv", options)
    importer = CsvImporter()
    series = importer.fetch_data(test_conf=test, selector=data_selector())
    assert len(series.data.keys()) == 2
    assert len(series.time) == 10
    assert len(series.data["m1"]) == 10
    assert len(series.data["m2"]) == 10
    assert len(series.attributes["commit"]) == 10


def test_import_csv_last_n_points():
    test = csv_test_config(SAMPLE_CSV)
    importer = CsvImporter()
    selector = data_selector()
    selector.last_n_points = 5
    series = importer.fetch_data(test, selector=selector)
    assert len(series.time) == 5
    assert len(series.data["m2"]) == 5
    assert len(series.attributes["commit"]) == 5


def test_import_histostat():
    test = HistoStatTestConfig(name="test", file="tests/resources/histostat.csv")
    importer = HistoStatImporter()
    series = importer.fetch_data(test)
    assert len(series.time) == 3
    assert len(series.data["initialize.result-success.count"]) == 3


def test_import_histostat_last_n_points():
    test = HistoStatTestConfig(name="test", file="tests/resources/histostat.csv")
    importer = HistoStatImporter()
    selector = DataSelector()
    selector.last_n_points = 2
    series = importer.fetch_data(test, selector=selector)
    assert len(series.time) == 2
    assert len(series.data["initialize.result-success.count"]) == 2


class MockPostgres:
    def fetch_data(self, query: str, params: tuple = None):
        return (
            ["time", "metric1", "metric2", "commit"],
            [
                (datetime(2022, 7, 1, 15, 11, tzinfo=pytz.UTC), 2, 3, "aaabbb"),
                (datetime(2022, 7, 2, 16, 22, tzinfo=pytz.UTC), 5, 6, "cccddd"),
                (datetime(2022, 7, 3, 17, 13, tzinfo=pytz.UTC), 2, 3, "aaaccc"),
                (datetime(2022, 7, 4, 18, 24, tzinfo=pytz.UTC), 5, 6, "ccc123"),
                (datetime(2022, 7, 5, 19, 15, tzinfo=pytz.UTC), 2, 3, "aaa493"),
                (datetime(2022, 7, 6, 20, 26, tzinfo=pytz.UTC), 5, 6, "cccfgl"),
                (datetime(2022, 7, 7, 21, 17, tzinfo=pytz.UTC), 2, 3, "aaalll"),
                (datetime(2022, 7, 8, 22, 28, tzinfo=pytz.UTC), 5, 6, "cccccc"),
                (datetime(2022, 7, 9, 23, 19, tzinfo=pytz.UTC), 2, 3, "aadddd"),
                (datetime(2022, 7, 10, 9, 29, tzinfo=pytz.UTC), 5, 6, "cciiii"),
            ],
        )


def test_import_postgres():
    test = PostgresTestConfig(
        name="test",
        query="SELECT * FROM sample;",
        time_column="time",
        metrics=[PostgresMetric("m1", 1, 1.0, "metric1"), PostgresMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )
    importer = PostgresImporter(MockPostgres())
    series = importer.fetch_data(test_conf=test, selector=data_selector())
    assert len(series.data.keys()) == 2
    assert len(series.time) == 10
    assert len(series.data["m1"]) == 10
    assert len(series.data["m2"]) == 10
    assert len(series.attributes["commit"]) == 10
    assert series.metrics["m2"].scale == 5.0


def test_import_postgres_with_time_filter():
    test = PostgresTestConfig(
        name="test",
        query="SELECT * FROM sample;",
        time_column="time",
        metrics=[PostgresMetric("m1", 1, 1.0, "metric1"), PostgresMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )

    importer = PostgresImporter(MockPostgres())
    selector = DataSelector()
    tz = pytz.timezone("Etc/GMT+1")
    selector.since_time = datetime(2022, 7, 8, 0, 0, 0, tzinfo=tz)
    selector.until_time = datetime(2022, 7, 10, 0, 0, 0, tzinfo=tz)
    series = importer.fetch_data(test, selector=selector)
    assert len(series.data.keys()) == 2
    assert len(series.time) == 2
    assert len(series.data["m1"]) == 2
    assert len(series.data["m2"]) == 2


def test_import_postgres_last_n_points():
    test = PostgresTestConfig(
        name="test",
        query="SELECT * FROM sample;",
        time_column="time",
        metrics=[PostgresMetric("m1", 1, 1.0, "metric1"), PostgresMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )

    importer = PostgresImporter(MockPostgres())
    selector = data_selector()
    selector.last_n_points = 5
    series = importer.fetch_data(test, selector=selector)
    assert len(series.time) == 5
    assert len(series.data["m2"]) == 5
    assert len(series.attributes["commit"]) == 5


class MockBigQuery:
    def fetch_data(self, query: str, params=None):
        return (
            ["time", "metric1", "metric2", "commit"],
            [
                (datetime(2022, 7, 1, 15, 11, tzinfo=pytz.UTC), 2, 3, "aaabbb"),
                (datetime(2022, 7, 2, 16, 22, tzinfo=pytz.UTC), 5, 6, "cccddd"),
                (datetime(2022, 7, 3, 17, 13, tzinfo=pytz.UTC), 2, 3, "aaaccc"),
                (datetime(2022, 7, 4, 18, 24, tzinfo=pytz.UTC), 5, 6, "ccc123"),
                (datetime(2022, 7, 5, 19, 15, tzinfo=pytz.UTC), 2, 3, "aaa493"),
                (datetime(2022, 7, 6, 20, 26, tzinfo=pytz.UTC), 5, 6, "cccfgl"),
                (datetime(2022, 7, 7, 21, 17, tzinfo=pytz.UTC), 2, 3, "aaalll"),
                (datetime(2022, 7, 8, 22, 28, tzinfo=pytz.UTC), 5, 6, "cccccc"),
                (datetime(2022, 7, 9, 23, 19, tzinfo=pytz.UTC), 2, 3, "aadddd"),
                (datetime(2022, 7, 10, 9, 29, tzinfo=pytz.UTC), 5, 6, "cciiii"),
            ],
        )


def test_import_bigquery():
    test = BigQueryTestConfig(
        name="test",
        query="SELECT * FROM sample;",
        time_column="time",
        metrics=[BigQueryMetric("m1", 1, 1.0, "metric1"), BigQueryMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )
    importer = BigQueryImporter(MockBigQuery())
    series = importer.fetch_data(test_conf=test, selector=data_selector())
    assert len(series.data.keys()) == 2
    assert len(series.time) == 10
    assert len(series.data["m1"]) == 10
    assert len(series.data["m2"]) == 10
    assert len(series.attributes["commit"]) == 10
    assert series.metrics["m2"].scale == 5.0


def test_import_bigquery_with_time_filter():
    test = BigQueryTestConfig(
        name="test",
        query="SELECT * FROM sample;",
        time_column="time",
        metrics=[BigQueryMetric("m1", 1, 1.0, "metric1"), BigQueryMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )

    importer = BigQueryImporter(MockBigQuery())
    selector = DataSelector()
    tz = pytz.timezone("Etc/GMT+1")
    selector.since_time = datetime(2022, 7, 8, 0, 0, 0, tzinfo=tz)
    selector.until_time = datetime(2022, 7, 10, 0, 0, 0, tzinfo=tz)
    series = importer.fetch_data(test, selector=selector)
    assert len(series.data.keys()) == 2
    assert len(series.time) == 2
    assert len(series.data["m1"]) == 2
    assert len(series.data["m2"]) == 2


def test_import_bigquery_last_n_points():
    test = BigQueryTestConfig(
        name="test",
        query="SELECT * FROM sample;",
        time_column="time",
        metrics=[BigQueryMetric("m1", 1, 1.0, "metric1"), BigQueryMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit"],
    )

    importer = BigQueryImporter(MockBigQuery())
    selector = data_selector()
    selector.last_n_points = 5
    series = importer.fetch_data(test, selector=selector)
    assert len(series.time) == 5
    assert len(series.data["m2"]) == 5
    assert len(series.attributes["commit"]) == 5


def test_graphite_substitutes_branch():
    config = GraphiteTestConfig(
        name="test",
        prefix="perf.%{BRANCH}.test",
        metrics=[GraphiteMetric("m1", 1, 1.0, "metric1", annotate=[])],
        tags=[],
        annotate=[]
    )
    assert config.get_path("feature-x", "m1") == "perf.feature-x.test.metric1"


def test_graphite_branch_placeholder_without_branch_raises_error():
    """Test that using %{BRANCH} in prefix without --branch raises an error."""
    config = GraphiteTestConfig(
        name="branch-test",
        prefix="perf.%{BRANCH}.test",
        metrics=[GraphiteMetric("m1", 1, 1.0, "metric1", annotate=[])],
        tags=[],
        annotate=[],
    )
    with pytest.raises(TestConfigError) as exc_info:
        config.get_path(None, "m1")
    assert "branch-test" in exc_info.value.message
    assert "%{BRANCH}" in exc_info.value.message
    assert "--branch" in exc_info.value.message


def test_postgres_branch_placeholder_without_branch_raises_error():
    """Test that using %{BRANCH} in query without --branch raises an error."""
    test = PostgresTestConfig(
        name="branch-test",
        query="SELECT * FROM results WHERE branch = '%{BRANCH}';",
        time_column="time",
        metrics=[PostgresMetric("m1", 1, 1.0, "metric1")],
        attributes=["commit"],
    )
    importer = PostgresImporter(MockPostgres())
    with pytest.raises(DataImportError) as exc_info:
        importer.fetch_data(test_conf=test, selector=data_selector())
    assert "branch-test" in exc_info.value.message
    assert "%{BRANCH}" in exc_info.value.message
    assert "--branch" in exc_info.value.message


def test_bigquery_branch_placeholder_without_branch_raises_error():
    """Test that using %{BRANCH} in query without --branch raises an error."""
    test = BigQueryTestConfig(
        name="branch-test",
        query="SELECT * FROM results WHERE branch = '%{BRANCH}';",
        time_column="time",
        metrics=[BigQueryMetric("m1", 1, 1.0, "metric1")],
        attributes=["commit"],
    )
    importer = BigQueryImporter(MockBigQuery())
    with pytest.raises(DataImportError) as exc_info:
        importer.fetch_data(test_conf=test, selector=data_selector())
    assert "branch-test" in exc_info.value.message
    assert "%{BRANCH}" in exc_info.value.message
    assert "--branch" in exc_info.value.message


# CSV branch handling tests

SAMPLE_SINGLE_BRANCH_CSV = "tests/resources/sample_single_branch.csv"
SAMPLE_MULTI_BRANCH_CSV = "tests/resources/sample_multi_branch.csv"


def csv_test_config_with_branch(file):
    """Create a CSV test config that includes the branch column in attributes."""
    return CsvTestConfig(
        name="test",
        file=file,
        csv_options=CsvOptions(),
        time_column="time",
        metrics=[CsvMetric("m1", 1, 1.0, "metric1"), CsvMetric("m2", 1, 5.0, "metric2")],
        attributes=["commit", "branch"],
    )


def test_csv_no_branch_no_branch_column():
    """No --branch specified and no branch column in CSV - should succeed."""
    importer = CsvImporter()
    series = importer.fetch_data(csv_test_config(SAMPLE_CSV), data_selector())
    assert len(series.time) == 10
    assert series.branch is None


def test_csv_no_branch_single_branch_in_column():
    """: No --branch specified but CSV has branch column with single value - should succeed."""
    importer = CsvImporter()
    series = importer.fetch_data(csv_test_config_with_branch(SAMPLE_SINGLE_BRANCH_CSV), data_selector())
    assert len(series.time) == 5
    assert series.branch is None


def test_csv_no_branch_multiple_branches_raises_error():
    """No --branch specified but CSV has branch column with multiple values - should error."""
    importer = CsvImporter()
    with pytest.raises(DataImportError) as exc_info:
        importer.fetch_data(csv_test_config_with_branch(SAMPLE_MULTI_BRANCH_CSV), data_selector())

    error_msg = exc_info.value.message
    assert "multiple branches" in error_msg
    assert "--branch" in error_msg
    assert "main" in error_msg
    assert "feature-x" in error_msg
    assert "feature-y" in error_msg


def test_csv_branch_specified_no_branch_column_raises_error():
    """--branch specified but CSV has no branch column - should error."""
    importer = CsvImporter()
    selector = data_selector()
    selector.branch = "main"

    with pytest.raises(DataImportError) as exc_info:
        importer.fetch_data(csv_test_config(SAMPLE_CSV), selector)

    error_msg = exc_info.value.message
    assert "--branch was specified" in error_msg
    assert "branch" in error_msg
    assert "column" in error_msg


def test_csv_branch_specified_filters_rows():
    """--branch specified and CSV has branch column - should filter rows."""
    importer = CsvImporter()

    # Filter by 'main' branch
    selector = data_selector()
    selector.branch = "main"
    series = importer.fetch_data(csv_test_config_with_branch(SAMPLE_MULTI_BRANCH_CSV), selector)
    assert len(series.time) == 4  # rows 1, 2, 5, 8 have 'main'
    assert series.branch == "main"

    # Filter by 'feature-x' branch
    selector = data_selector()
    selector.branch = "feature-x"
    series = importer.fetch_data(csv_test_config_with_branch(SAMPLE_MULTI_BRANCH_CSV), selector)
    assert len(series.time) == 2  # rows 3, 4 have 'feature-x'
    assert series.branch == "feature-x"

    # Filter by 'feature-y' branch
    selector = data_selector()
    selector.branch = "feature-y"
    series = importer.fetch_data(csv_test_config_with_branch(SAMPLE_MULTI_BRANCH_CSV), selector)
    assert len(series.time) == 2  # rows 6, 7 have 'feature-y'
    assert series.branch == "feature-y"
