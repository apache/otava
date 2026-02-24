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
import os
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest
from e2e_test_utils import _remove_trailing_whitespaces, container

CARBON_PORT = 2003
HTTP_PORT = 80


def test_analyze_graphite():
    """
    End-to-end test for the Graphite example from docs/GRAPHITE.md.

    Starts Graphite docker container, writes sample data, then runs otava analyze,
    and verifies the output contains expected change points.
    """
    with container(
        "graphiteapp/graphite-statsd",
        ports=[HTTP_PORT, CARBON_PORT],
        readiness_check=_graphite_readiness_check,
    ) as (container_id, port_map):
        # Seed data into Graphite using the same pattern as datagen.sh
        data_points = _seed_graphite_data(port_map[CARBON_PORT])

        # Wait for data to be written and available
        _wait_for_graphite_data(
            http_port=port_map[HTTP_PORT],
            metric_path="performance-tests.daily.my-product.client.throughput",
            expected_points=data_points,
        )

        # Run the Otava analysis
        proc = subprocess.run(
            ["uv", "run", "otava", "analyze", "my-product.test", "--since=-10m"],
            capture_output=True,
            text=True,
            timeout=600,
            env=dict(
                os.environ,
                OTAVA_CONFIG=str(Path("examples/graphite/config/otava.yaml")),
                GRAPHITE_ADDRESS=f"http://localhost:{port_map[HTTP_PORT]}/",
                GRAFANA_ADDRESS="http://localhost:3000/",
                GRAFANA_USER="admin",
                GRAFANA_PASSWORD="admin",
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

        # Verify output contains expected columns and change point indicators
        output = _remove_trailing_whitespaces(proc.stdout)

        # Check that the header contains expected column names
        assert "throughput" in output
        assert "response_time" in output
        assert "cpu_usage" in output

        # Data shows throughput dropped from ~61k to ~57k (-5.6%) and cpu increased from 0.2 to 0.8 (+300%)
        assert "-5.6%" in output  # throughput change
        assert "+300.0%" in output  # cpu_usage change


def _graphite_readiness_check(container_id: str, port_map: dict[int, int]) -> bool:
    """
    Check if Graphite is fully ready by writing a canary metric and verifying it's queryable.

    This ensures both Carbon (write path) and Graphite-web (read path) are operational.
    """
    carbon_port = port_map[CARBON_PORT]
    http_port = port_map[HTTP_PORT]

    # Send a canary metric to Carbon
    timestamp = int(time.time())
    canary_metrics = "test.canary.readiness"
    message = f"{canary_metrics} 1 {timestamp}\n"
    try:
        with socket.create_connection(("localhost", carbon_port), timeout=5) as sock:
            sock.sendall(message.encode("utf-8"))
    except OSError:
        return False

    # Check if the canary metric is queryable via Graphite-web
    url = f"http://localhost:{http_port}/render?target={canary_metrics}&format=json&from=-1min"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data and len(data) > 0:
                datapoints = data[0].get("datapoints", [])
                # Check if we have at least one non-null data point
                if any(dp[0] is not None for dp in datapoints):
                    return True
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        pass

    return False


def _seed_graphite_data(
    carbon_port: int,
    prefix: str = "performance-tests.daily.my-product",
) -> int:
    """
    Seed Graphite with test data matching the pattern from examples/graphite/datagen/datagen.sh.

    Data pattern (from newest to oldest, matching datagen.sh array order):
    - throughput: 56950, 57980, 57123, 60960, 60160, 61160 (index 0 is newest)
    - response_time (p50): 85, 87, 88, 89, 85, 87
    - cpu_usage: 0.7, 0.9, 0.8, 0.1, 0.3, 0.2

    When displayed chronologically (oldest to newest), this shows:
    - throughput dropped from ~61k to ~57k (-5.6% regression)
    - cpu increased from 0.2 to 0.8 (+300% regression)
    """
    throughput_path = f"{prefix}.client.throughput"
    throughput_values = [56950, 57980, 57123, 60960, 60160, 61160]

    p50_path = f"{prefix}.client.p50"
    p50_values = [85, 87, 88, 89, 85, 87]

    cpu_path = f"{prefix}.server.cpu"
    cpu_values = [0.7, 0.9, 0.8, 0.1, 0.3, 0.2]

    start_timestamp = int(time.time())
    num_points = len(throughput_values)

    for i in range(num_points):
        # Data is sent from newest to oldest (same as datagen.sh)
        timestamp = start_timestamp - (i * 60)
        _send_to_graphite(carbon_port, throughput_path, throughput_values[i], timestamp)
        _send_to_graphite(carbon_port, p50_path, p50_values[i], timestamp)
        _send_to_graphite(carbon_port, cpu_path, cpu_values[i], timestamp)
    return num_points


def _send_to_graphite(carbon_port: int, path: str, value: float, timestamp: int):
    """
    Send a single metric to Graphite via the Carbon plaintext protocol.
    """
    message = f"{path} {value} {timestamp}\n"
    try:
        with socket.create_connection(("localhost", carbon_port), timeout=5) as sock:
            sock.sendall(message.encode("utf-8"))
    except OSError as e:
        pytest.fail(f"Failed to send metric to Graphite: {e}")


def _wait_for_graphite_data(
    http_port: int,
    metric_path: str,
    expected_points: int,
    timeout: float = 120,
    poll_interval: float = 0.5,
) -> None:
    """
    Wait for Graphite to have the expected data points available.

    Polls the Graphite render API until the specified metric has at least
    the expected number of non-null data points, or until the timeout expires.
    """
    url = f"http://localhost:{http_port}/render?target={metric_path}&format=json&from=-10min"
    deadline = time.time() + timeout

    last_observed_count = 0
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
                if data and len(data) > 0:
                    datapoints = data[0].get("datapoints", [])
                    # Count non-null values
                    non_null_count = sum(1 for dp in datapoints if dp[0] is not None)
                    last_observed_count = non_null_count
                    if non_null_count >= expected_points:
                        return
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            pass  # Retry on connection errors

        time.sleep(poll_interval)

    pytest.fail(
        f"Timeout waiting for Graphite data. "
        f"Expected {expected_points} points for metric '{metric_path}' within {timeout}s, got {last_observed_count}"
    )


def test_analyze_graphite_with_branch():
    """
    End-to-end test for Graphite with %{BRANCH} substitution.

    Verifies that using --branch correctly substitutes %{BRANCH} in the prefix
    to fetch data from a branch-specific Graphite path.
    """
    with container(
        "graphiteapp/graphite-statsd",
        ports=[HTTP_PORT, CARBON_PORT],
        readiness_check=_graphite_readiness_check,
    ) as (container_id, port_map):
        # Seed data into a branch-specific path
        branch_name = "feature-xyz"
        prefix = f"performance-tests.{branch_name}.my-product"
        data_points = _seed_graphite_data(port_map[CARBON_PORT], prefix=prefix)

        # Wait for data to be written and available
        _wait_for_graphite_data(
            http_port=port_map[HTTP_PORT],
            metric_path=f"performance-tests.{branch_name}.my-product.client.throughput",
            expected_points=data_points,
        )

        # Create a temporary config file with %{BRANCH} in the prefix
        config_content = """
tests:
  branch-test:
    type: graphite
    prefix: performance-tests.%{BRANCH}.my-product
    tags: [perf-test, branch]
    metrics:
      throughput:
        suffix: client.throughput
        direction: 1
        scale: 1
      response_time:
        suffix: client.p50
        direction: -1
        scale: 1
      cpu_usage:
        suffix: server.cpu
        direction: -1
        scale: 1
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as config_file:
            config_file.write(config_content)
            config_file_path = config_file.name

        try:
            # Run the Otava analysis with --branch
            proc = subprocess.run(
                [
                    "uv",
                    "run",
                    "otava",
                    "analyze",
                    "branch-test",
                    "--branch",
                    branch_name,
                    "--since=-10m",
                ],
                capture_output=True,
                text=True,
                timeout=600,
                env=dict(
                    os.environ,
                    OTAVA_CONFIG=config_file_path,
                    GRAPHITE_ADDRESS=f"http://localhost:{port_map[HTTP_PORT]}/",
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

            # Verify output contains expected columns
            output = _remove_trailing_whitespaces(proc.stdout)

            # Check that the header contains expected column names
            assert "throughput" in output
            assert "response_time" in output
            assert "cpu_usage" in output

            # Data shows throughput dropped from ~61k to ~57k (-5.6%) and cpu increased +300%
            assert "-5.6%" in output  # throughput change
            assert "+300.0%" in output  # cpu_usage change

        finally:
            os.unlink(config_file_path)
