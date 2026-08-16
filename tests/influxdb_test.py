# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0

import os
from datetime import datetime, timezone
from unittest.mock import Mock

import pyarrow as pa
import pytest

from otava.config import load_config_from_file
from otava.data_selector import DataSelector
from otava.importer import DataImportError, InfluxDBImporter
from otava.influxdb import InfluxDB, InfluxDBConfig
from otava.main import create_otava_cli_parser
from otava.test_config import (
    InfluxDBMetric,
    InfluxDBTestConfig,
    TestConfigError,
    create_test_config,
)


def selector():
    result = DataSelector()
    result.since_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
    result.until_time = datetime(2024, 1, 5, tzinfo=timezone.utc)
    return result


def test_influxdb_connection_config_precedence(tmp_path, monkeypatch):
    config_file = tmp_path / "otava.yaml"
    config_file.write_text(
        "influxdb:\n  host: yaml-host\n  database: yaml-db\n  token: yaml-token\n"
    )
    monkeypatch.setenv("INFLUXDB_HOST", "env-host")
    monkeypatch.setenv("INFLUXDB_DATABASE", "env-db")
    monkeypatch.setenv("INFLUXDB_TOKEN", "env-token")

    config = load_config_from_file(
        str(config_file),
        arg_overrides=["--influxdb-host", "cli-host", "--influxdb-token", "cli-token"],
    )
    assert config.influxdb.host == "cli-host"
    assert config.influxdb.database == "env-db"
    assert config.influxdb.token == "cli-token"
    assert os.environ["INFLUXDB_HOST"] == "env-host"


def test_cli_help_includes_influxdb_options():
    help_text = create_otava_cli_parser().format_help()
    assert "InfluxDB Options:" in help_text
    assert "--influxdb-host" in help_text
    assert "--influxdb-database" in help_text
    assert "--influxdb-token" in help_text


def test_influxdb_test_config_defaults_to_sql_and_parses_metrics():
    test = create_test_config(
        "latency",
        {
            "type": "influxdb",
            "query": "SELECT * FROM latency",
            "attributes": ["branch"],
            "metrics": {"p95": {"column": "p95_ms", "direction": -1, "scale": 0.001}},
        },
    )
    assert isinstance(test, InfluxDBTestConfig)
    assert test.query_language == "sql"
    assert test.metrics["p95"] == InfluxDBMetric("p95", -1, 0.001, "p95_ms")


def test_influxdb_test_config_supports_influxql_and_rejects_unknown_language():
    test = create_test_config(
        "latency",
        {"type": "influxdb", "query": "SELECT * FROM latency", "metrics": ["p95_ms"], "query_language": "influxql"},
    )
    assert test.query_language == "influxql"
    with pytest.raises(TestConfigError):
        create_test_config(
            "latency",
            {"type": "influxdb", "query": "SELECT * FROM latency", "metrics": ["p95_ms"], "query_language": "flux"},
        )


def test_influxdb_importer_reads_arrow_table_and_applies_selection():
    client = Mock()
    client.query.return_value = pa.table(
        {
            "time": [
                datetime(2023, 12, 31, tzinfo=timezone.utc),
                datetime(2024, 1, 2, tzinfo=timezone.utc),
                datetime(2024, 1, 3, tzinfo=timezone.utc),
                datetime(2024, 1, 5, tzinfo=timezone.utc),
            ],
            "branch": ["main", "main", "main", "main"],
            "commit": ["before", "b", "c", "after"],
            "p95_ms": [10, 20, 30, 40],
        }
    )
    backend = InfluxDB(InfluxDBConfig("host", "database", "token"))
    backend._client = client
    test = InfluxDBTestConfig(
        "latency",
        "SELECT * FROM latency",
        metrics=[InfluxDBMetric("p95", -1, 0.001, "p95_ms")],
        attributes=["branch", "commit"],
    )
    chosen = selector()
    chosen.metrics = ["p95"]
    chosen.last_n_points = 2
    series = InfluxDBImporter(backend).fetch_data(test, chosen)

    assert series.branch is None
    assert series.data == {"p95": [20.0, 30.0]}
    assert series.attributes == {"branch": ["main", "main"], "commit": ["b", "c"]}
    assert client.query.call_args.kwargs == {"query": "SELECT * FROM latency", "language": "sql"}


def test_influxdb_importer_executes_influxql_and_escapes_branch():
    backend = Mock()
    backend.fetch_data.return_value = (
        ["time", "p95_ms"],
        [(datetime(2024, 1, 2, tzinfo=timezone.utc), 4)],
    )
    test = InfluxDBTestConfig(
        "latency",
        "SELECT * FROM latency WHERE branch = %{BRANCH}",
        query_language="influxql",
        metrics=[InfluxDBMetric("p95", 1, 1.0, "p95_ms")],
    )
    chosen = selector()
    chosen.branch = "release'candidate"
    series = InfluxDBImporter(backend).fetch_data(test, chosen)
    assert series.data["p95"] == [4.0]
    assert "branch = 'release''candidate'" in backend.fetch_data.call_args.args[0]
    assert backend.fetch_data.call_args.args[1] == "influxql"


def test_influxdb_importer_reports_missing_columns_and_client_errors():
    test = InfluxDBTestConfig(
        "latency",
        "SELECT * FROM latency",
        metrics=[InfluxDBMetric("p95", 1, 1.0, "missing")],
    )
    backend = Mock()
    backend.fetch_data.return_value = (["time"], [])
    with pytest.raises(DataImportError) as missing_error:
        InfluxDBImporter(backend).fetch_data(test, selector())
    assert missing_error.value.message == "Column not found 'missing' is not in list"

    backend.fetch_data.side_effect = RuntimeError("server unavailable")
    with pytest.raises(DataImportError) as client_error:
        InfluxDBImporter(backend).fetch_data(
            InfluxDBTestConfig(
                "latency", "SELECT * FROM latency", metrics=[InfluxDBMetric("p95", 1, 1.0, "p95_ms")]
            ),
            selector(),
        )
    assert "latency" in client_error.value.message
    assert "server unavailable" in client_error.value.message
