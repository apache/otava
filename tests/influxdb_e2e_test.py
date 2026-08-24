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
from datetime import datetime, timezone
from pathlib import Path

import pytest
from e2e_test_utils import container

from otava.config import load_config_from_file
from otava.data_selector import DataSelector
from otava.importer import InfluxDBImporter
from otava.influxdb import InfluxDB

INFLUXDB_IMAGE = "influxdb:3.11.2-core"
INFLUXDB_PORT = 8181
INFLUXDB_TOKEN = "apiv3_otava_example_admin_token_2026"
EXAMPLE_DIR = Path("examples/influxdb").resolve()


def test_influxdb_sql_and_influxql_return_identical_seeded_data():
    with container(
        INFLUXDB_IMAGE,
        command=[
            "influxdb3",
            "serve",
            "--node-id=otava-e2e",
            "--object-store=memory",
            "--admin-token-file=/example/admin-token.json",
        ],
        ports=[INFLUXDB_PORT],
        volumes={str(EXAMPLE_DIR): "/example:ro"},
    ) as (container_id, port_map):
        seed = subprocess.run(
            [
                "docker",
                "exec",
                "--env",
                f"INFLUXDB3_HOST_URL=http://127.0.0.1:{INFLUXDB_PORT}",
                "--env",
                f"INFLUXDB3_AUTH_TOKEN={INFLUXDB_TOKEN}",
                "--env",
                "INFLUXDB3_DATABASE_NAME=performance",
                container_id,
                "/bin/sh",
                "/example/seed.sh",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if seed.returncode != 0:
            pytest.fail(
                "InfluxDB seed command returned non-zero exit code.\n\n"
                f"Command: {seed.args!r}\n"
                f"Exit code: {seed.returncode}\n\n"
                f"Stdout:\n{seed.stdout}\n\n"
                f"Stderr:\n{seed.stderr}\n"
            )

        host = f"http://localhost:{port_map[INFLUXDB_PORT]}"
        config = load_config_from_file(
            str(EXAMPLE_DIR / "otava.yaml"),
            arg_overrides=[
                "--influxdb-host",
                host,
                "--influxdb-token",
                INFLUXDB_TOKEN,
            ],
        )
        importer = InfluxDBImporter(InfluxDB(config.influxdb))
        selector = DataSelector()
        selector.branch = "main"
        selector.since_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
        selector.until_time = datetime(2025, 1, 7, tzinfo=timezone.utc)

        sql = importer.fetch_data(config.tests["api_latency_sql"], selector)
        influxql = importer.fetch_data(config.tests["api_latency_influxql"], selector)

        expected_times = [
            datetime(2025, 1, day, tzinfo=timezone.utc).timestamp()
            for day in range(1, 7)
        ]
        expected_attributes = {
            "branch": ["main"] * 6,
            "commit": ["a1b2c3d", "b2c3d4e", "c3d4e5f", "d4e5f6a", "e5f6a7b", "f6a7b8c"],
        }
        expected_data = {"p95": [87.0, 85.0, 89.0, 118.0, 121.0, 119.0]}

        assert sql.branch == influxql.branch == "main"
        assert sql.time == influxql.time == expected_times
        assert sql.attributes == influxql.attributes == expected_attributes
        assert sql.data == influxql.data == expected_data
        assert sql.metrics == influxql.metrics
