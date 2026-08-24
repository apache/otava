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

import os
import subprocess
import textwrap
from pathlib import Path

import pytest
from e2e_test_utils import _remove_trailing_whitespaces, container

INFLUXDB_IMAGE = "influxdb:3.11.2-core"
INFLUXDB_PORT = 8181
INFLUXDB_TOKEN = "apiv3_otava_example_admin_token_2026"
EXAMPLE_DIR = Path("examples/influxdb").resolve()


def _analyze(test_name: str, host: str) -> str:
    command = [
        "uv",
        "run",
        "otava",
        "analyze",
        test_name,
        "--influxdb-host",
        host,
        "--influxdb-database",
        "performance",
        "--influxdb-token",
        INFLUXDB_TOKEN,
        "--branch",
        "main",
        "--since",
        "2025-01-01T00:00:00Z",
        "--until",
        "2025-01-07T00:00:00Z",
    ]
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=600,
        env=dict(os.environ, OTAVA_CONFIG=str(EXAMPLE_DIR / "otava.yaml")),
    )
    if proc.returncode != 0:
        pytest.fail(
            "InfluxDB analysis command returned non-zero exit code.\n\n"
            f"Command: {proc.args!r}\n"
            f"Exit code: {proc.returncode}\n\n"
            f"Stdout:\n{proc.stdout}\n\n"
            f"Stderr:\n{proc.stderr}\n"
        )
    return _remove_trailing_whitespaces(proc.stdout)


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

        expected_output = textwrap.dedent(
            """\
            time                       branch    commit      p95
            -------------------------  --------  --------  -----
            2025-01-01 00:00:00 +0000  main      a1b2c3d      87
            2025-01-02 00:00:00 +0000  main      b2c3d4e      85
            2025-01-03 00:00:00 +0000  main      c3d4e5f      89
                                                           ·····
                                                           +37.2%
                                                           ·····
            2025-01-04 00:00:00 +0000  main      d4e5f6a     118
            2025-01-05 00:00:00 +0000  main      e5f6a7b     121
            2025-01-06 00:00:00 +0000  main      f6a7b8c     119
            """
        ).rstrip("\n")

        host = f"http://localhost:{port_map[INFLUXDB_PORT]}"
        outputs = [
            _analyze(test_name, host)
            for test_name in ("api_latency_sql", "api_latency_influxql")
        ]
        assert outputs == [expected_output, expected_output]
