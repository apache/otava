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

import subprocess
import sys
import textwrap
from importlib import import_module, metadata
from pathlib import Path

import pytest


def test_development_dependencies_are_not_published_as_an_extra():
    published_extras = metadata.metadata("apache-otava").get_all("Provides-Extra") or []

    assert "dev" not in published_extras


def test_pytz_is_declared_as_a_runtime_dependency():
    requirements = metadata.requires("apache-otava") or []

    assert any(
        requirement.lower().startswith("pytz") and "extra ==" not in requirement
        for requirement in requirements
    )


def test_missing_optional_dependency_names_install_extra(monkeypatch):
    optional = import_module("otava._optional")

    def missing_google(_):
        raise ModuleNotFoundError("No module named 'google'", name="google")

    monkeypatch.setattr(optional, "import_module", missing_google)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        optional.import_optional_dependency("google.cloud.bigquery", "bigquery")

    assert str(exc_info.value) == (
        "Optional dependency 'google.cloud.bigquery' is required for this operation. "
        "Install it with: pip install 'apache-otava[bigquery]'"
    )


def test_optional_dependency_preserves_unrelated_import_failure(monkeypatch):
    optional = import_module("otava._optional")
    original_error = ModuleNotFoundError("No module named 'transitive_package'", name="transitive_package")

    def missing_transitive(_):
        raise original_error

    monkeypatch.setattr(optional, "import_module", missing_transitive)

    with pytest.raises(ModuleNotFoundError) as exc_info:
        optional.import_optional_dependency("google.cloud.bigquery", "bigquery")

    assert exc_info.value is original_error


def test_cli_import_does_not_load_optional_service_clients():
    script = textwrap.dedent(
        """
        import builtins

        blocked = {"google", "influxdb_client_3", "pg8000", "requests", "slack_sdk"}
        original_import = builtins.__import__

        def import_without_optional_clients(name, globals=None, locals=None, fromlist=(), level=0):
            top_level = name.partition(".")[0]
            if top_level in blocked:
                raise ModuleNotFoundError(f"No module named '{top_level}'", name=top_level)
            return original_import(name, globals, locals, fromlist, level)

        builtins.__import__ = import_without_optional_clients

        from otava.main import create_otava_cli_parser

        assert "usage:" in create_otava_cli_parser().format_help()
        """
    )

    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_runtime_type_hints_do_not_require_optional_service_clients():
    script = textwrap.dedent(
        """
        import builtins
        from typing import get_type_hints

        blocked = {"google", "influxdb_client_3", "pg8000", "slack_sdk"}
        original_import = builtins.__import__

        def import_without_optional_clients(name, globals=None, locals=None, fromlist=(), level=0):
            top_level = name.partition(".")[0]
            if top_level in blocked:
                raise ModuleNotFoundError(f"No module named '{top_level}'", name=top_level)
            return original_import(name, globals, locals, fromlist, level)

        builtins.__import__ = import_without_optional_clients

        from otava.bigquery import BigQuery
        from otava.influxdb import InfluxDB
        from otava.postgres import Postgres
        from otava.slack import SlackNotifier

        get_type_hints(BigQuery.client.fget)
        get_type_hints(InfluxDB.client.fget)
        get_type_hints(Postgres._Postgres__get_conn)
        get_type_hints(SlackNotifier.__init__)
        """
    )

    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_missing_influxdb_extra_causes_cli_failure(monkeypatch, caplog):
    optional = import_module("otava._optional")

    def missing_influxdb(module_name):
        assert module_name == "influxdb_client_3"
        raise ModuleNotFoundError(
            "No module named 'influxdb_client_3'",
            name="influxdb_client_3",
        )

    monkeypatch.setattr(optional, "import_module", missing_influxdb)

    from otava.main import script_main

    config = Path(__file__).parents[1] / "examples/influxdb/otava.yaml"
    args = [
        "analyze",
        "--config-file",
        str(config),
        "api_latency_sql",
        "--branch",
        "main",
        "--influxdb-host",
        "http://localhost:8181",
        "--influxdb-database",
        "performance",
        "--influxdb-token",
        "token",
    ]

    with pytest.raises(SystemExit) as exc_info:
        script_main(args=args)

    assert exc_info.value.code == 1
    assert "pip install 'apache-otava[influxdb]'" in caplog.text
