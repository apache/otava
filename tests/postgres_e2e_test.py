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
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import pytest
from e2e_test_utils import _remove_trailing_whitespaces, container


def test_analyze():
    """
    End-to-end test for the PostgreSQL example.

    Starts the docker-compose stack from examples/postgresql/docker-compose.yaml,
    waits for Postgres to be ready, runs the otava analysis in a one-off
    container, and compares stdout to the expected output (seeded data uses
    deterministic 2025 timestamps).
    """
    username = "exampleuser"
    password = "examplepassword"
    db = "benchmark_results"
    with postgres_container(username, password, db) as (postgres_container_id, host_port):
        # Run the Otava analysis
        proc = subprocess.run(
            ["uv", "run", "otava", "analyze", "aggregate_mem", "--branch", "trunk"],
            capture_output=True,
            text=True,
            timeout=600,
            env=dict(
                os.environ,
                OTAVA_CONFIG=Path("examples/postgresql/config/otava.yaml"),
                POSTGRES_HOSTNAME="localhost",
                POSTGRES_PORT=host_port,
                POSTGRES_USERNAME=username,
                POSTGRES_PASSWORD=password,
                POSTGRES_DATABASE=db,
            ),
        )

        if proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {proc.args!r}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"Stdout:\n{proc.stdout}\n\n"
                f"Stderr:\n{proc.stderr}\n"
            )

        expected_output = textwrap.dedent(
            """\
time                       experiment_id       commit      config_id    process_cumulative_rate_mean    process_cumulative_rate_stderr    process_cumulative_rate_diff
-------------------------  ------------------  --------  -----------  ------------------------------  --------------------------------  ------------------------------
2025-03-13 10:03:02 +0000  aggregate-36e5ccd2  36e5ccd2            1                           61160                              2052                           13558
2025-03-25 10:03:02 +0000  aggregate-d5460f38  d5460f38            1                           60160                              2142                           13454
2025-04-02 10:03:02 +0000  aggregate-bc9425cb  bc9425cb            1                           60960                              2052                           13053
                                                                      ······························
                                                                                               -5.6%
                                                                      ······························
2025-04-06 10:03:02 +0000  aggregate-14df1b11  14df1b11            1                           57123                              2052                           14052
2025-04-13 10:03:02 +0000  aggregate-ac40c0d8  ac40c0d8            1                           57980                              2052                           13521
2025-04-27 10:03:02 +0000  aggregate-0af4ccbc  0af4ccbc            1                           56950                              2052                           13532
        """
        )
        assert _remove_trailing_whitespaces(proc.stdout) == expected_output.rstrip("\n")

        # Verify the DB was updated with the detected change.
        # Query the updated change metric at the detected change point.
        query_proc = subprocess.run(
            [
                "docker",
                "exec",
                postgres_container_id,
                "psql",
                "-U",
                "exampleuser",
                "-d",
                "benchmark_results",
                "-Atc",
                """
             SELECT
                process_cumulative_rate_mean_rel_forward_change,
                process_cumulative_rate_mean_rel_backward_change,
                process_cumulative_rate_mean_p_value
             FROM results
              WHERE experiment_id='aggregate-14df1b11' AND config_id=1;
             """,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if query_proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {query_proc.args!r}\n"
                f"Exit code: {query_proc.returncode}\n\n"
                f"Stdout:\n{query_proc.stdout}\n\n"
                f"Stderr:\n{query_proc.stderr}\n"
            )

        # psql -Atc returns rows like: value|pvalue
        forward_change, backward_change, p_value = query_proc.stdout.strip().split("|")
        # --update-postgres was not specified, so no change point should be recorded
        assert forward_change == backward_change == p_value == ""


def test_analyze_and_update_postgres():
    """
    End-to-end test for the PostgreSQL example.

    Starts the docker-compose stack from examples/postgresql/docker-compose.yaml,
    waits for Postgres to be ready, runs the otava analysis in a one-off
    container, and compares stdout to the expected output (seeded data uses
    deterministic 2025 timestamps).
    """

    username = "exampleuser"
    password = "examplepassword"
    db = "benchmark_results"
    with postgres_container(username, password, db) as (postgres_container_id, host_port):
        # Run the Otava analysis
        proc = subprocess.run(
            ["uv", "run", "otava", "analyze", "aggregate_mem", "--branch", "trunk", "--update-postgres"],
            capture_output=True,
            text=True,
            timeout=600,
            env=dict(
                os.environ,
                OTAVA_CONFIG=Path("examples/postgresql/config/otava.yaml"),
                POSTGRES_HOSTNAME="localhost",
                POSTGRES_PORT=host_port,
                POSTGRES_USERNAME=username,
                POSTGRES_PASSWORD=password,
                POSTGRES_DATABASE=db,
            ),
        )

        if proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {proc.args!r}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"Stdout:\n{proc.stdout}\n\n"
                f"Stderr:\n{proc.stderr}\n"
            )

        expected_output = textwrap.dedent(
            """\
    time                       experiment_id       commit      config_id    process_cumulative_rate_mean    process_cumulative_rate_stderr    process_cumulative_rate_diff
    -------------------------  ------------------  --------  -----------  ------------------------------  --------------------------------  ------------------------------
    2025-03-13 10:03:02 +0000  aggregate-36e5ccd2  36e5ccd2            1                           61160                              2052                           13558
    2025-03-25 10:03:02 +0000  aggregate-d5460f38  d5460f38            1                           60160                              2142                           13454
    2025-04-02 10:03:02 +0000  aggregate-bc9425cb  bc9425cb            1                           60960                              2052                           13053
                                                                          ······························
                                                                                                   -5.6%
                                                                          ······························
    2025-04-06 10:03:02 +0000  aggregate-14df1b11  14df1b11            1                           57123                              2052                           14052
    2025-04-13 10:03:02 +0000  aggregate-ac40c0d8  ac40c0d8            1                           57980                              2052                           13521
    2025-04-27 10:03:02 +0000  aggregate-0af4ccbc  0af4ccbc            1                           56950                              2052                           13532
            """
        )
        assert _remove_trailing_whitespaces(proc.stdout) == expected_output.rstrip("\n")

        # Verify the DB was updated with the detected change.
        # Query the updated change metric at the detected change point.
        query_proc = subprocess.run(
            [
                "docker",
                "exec",
                postgres_container_id,
                "psql",
                "-U",
                "exampleuser",
                "-d",
                "benchmark_results",
                "-Atc",
                """
             SELECT
                 process_cumulative_rate_mean_rel_forward_change,
                 process_cumulative_rate_mean_rel_backward_change,
                 process_cumulative_rate_mean_p_value
             FROM results
             WHERE experiment_id='aggregate-14df1b11' AND config_id=1;
             """,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if query_proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {query_proc.args!r}\n"
                f"Exit code: {query_proc.returncode}\n\n"
                f"Stdout:\n{query_proc.stdout}\n\n"
                f"Stderr:\n{query_proc.stderr}\n"
            )

        # psql -Atc returns rows like: value|pvalue
        forward_change, backward_change, p_value = query_proc.stdout.strip().split("|")
        forward_change = float(forward_change)
        backward_change = float(backward_change)
        p_value = float(p_value)

        if abs(forward_change - (-5.6)) > 0.2:
            pytest.fail(f"DB change value {forward_change!r} not within tolerance of -5.6")
        if abs(backward_change - 5.94) > 0.2:
            pytest.fail(f"DB backward change {backward_change!r} not within tolerance of 5.94")
        if p_value >= 0.001:
            pytest.fail(f"DB p-value {p_value!r} not less than 0.01")


def _postgres_readiness_check_f(
    username: str, database: str
) -> Callable[[str, dict[int, int]], bool]:
    """Check if PostgreSQL is ready to accept connections."""

    def _inner(
        container_id: str,
        port_map: dict[int, int],
    ) -> bool:
        cmd = [
            "docker",
            "exec",
            container_id,
            "pg_isready",
            "-U",
            username,
            "-d",
            database,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc.returncode == 0

    return _inner


@contextmanager
def postgres_container(username, password, database):
    """
    Context manager for running a PostgreSQL container.
    Yields the container ID and ensures cleanup on exit.
    """
    with container(
        "postgres:latest",
        env={
            "POSTGRES_USER": username,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_DB": database,
        },
        ports=[5432],
        volumes={
            str(Path("examples/postgresql/init-db").resolve()): "/docker-entrypoint-initdb.d",
        },
        readiness_check=_postgres_readiness_check_f(username, database),
    ) as (container_id, port_map):
        yield container_id, str(port_map[5432])
