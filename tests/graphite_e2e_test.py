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
import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path

import pytest


def test_analyze_graphite():
    """
    End-to-end test for the Graphite example from docs/GRAPHITE.md.

    Starts Graphite docker container, writes sample data, then runs otava analyze,
    and verifies the output contains expected change points.
    """
    with graphite_container() as graphite_port:
        # Run the Otava analysis
        proc = subprocess.run(
            ["uv", "run", "otava", "analyze", "my-product.test", "--since=-10m"],
            capture_output=True,
            text=True,
            timeout=600,
            env=dict(
                os.environ,
                OTAVA_CONFIG=str(Path("examples/graphite/config/otava.yaml")),
                GRAPHITE_ADDRESS=f"http://localhost:{graphite_port}/",
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


@contextmanager
def graphite_container():
    """
    Context manager for running a Graphite container with seeded data.
    Yields the Graphite HTTP port and ensures cleanup on exit.
    """
    if not shutil.which("docker"):
        pytest.fail("docker is not available on PATH")

    container_id = None
    try:
        # Start graphite container
        cmd = [
            "docker",
            "run",
            "-d",
            "--publish",
            "80",
            "--publish",
            "2003",
            "graphiteapp/graphite-statsd",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            pytest.fail(
                "Docker command returned non-zero exit code.\n\n"
                f"Command: {cmd!r}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"Stdout:\n{proc.stdout}\n\n"
                f"Stderr:\n{proc.stderr}\n"
            )
        container_id = proc.stdout.strip()

        # Determine the randomly assigned host port for 80/tcp (HTTP)
        inspect_cmd = [
            "docker",
            "inspect",
            "-f",
            '{{ (index (index .NetworkSettings.Ports "80/tcp") 0).HostPort }}',
            container_id,
        ]
        inspect_proc = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=60)
        if inspect_proc.returncode != 0:
            pytest.fail(
                "Docker inspect returned non-zero exit code.\n\n"
                f"Command: {inspect_cmd!r}\n"
                f"Exit code: {inspect_proc.returncode}\n\n"
                f"Stdout:\n{inspect_proc.stdout}\n\n"
                f"Stderr:\n{inspect_proc.stderr}\n"
            )
        http_port = inspect_proc.stdout.strip()

        # Determine the randomly assigned host port for 2003/tcp (Carbon)
        inspect_cmd = [
            "docker",
            "inspect",
            "-f",
            '{{ (index (index .NetworkSettings.Ports "2003/tcp") 0).HostPort }}',
            container_id,
        ]
        inspect_proc = subprocess.run(inspect_cmd, capture_output=True, text=True, timeout=60)
        if inspect_proc.returncode != 0:
            pytest.fail(
                "Docker inspect returned non-zero exit code.\n\n"
                f"Command: {inspect_cmd!r}\n"
                f"Exit code: {inspect_proc.returncode}\n\n"
                f"Stdout:\n{inspect_proc.stdout}\n\n"
                f"Stderr:\n{inspect_proc.stderr}\n"
            )
        carbon_port = int(inspect_proc.stdout.strip())

        # Wait until Graphite HTTP responds
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            try:
                with socket.create_connection(("localhost", int(http_port)), timeout=1):
                    ready = True
                    break
            except OSError:
                time.sleep(1)

        if not ready:
            pytest.fail("Graphite HTTP port did not become ready within timeout.")

        # Wait a bit more for Graphite to fully initialize
        time.sleep(5)

        # Seed data into Graphite using the same pattern as datagen.sh
        _seed_graphite_data(carbon_port)

        # Wait for data to be written and available
        time.sleep(5)

        yield http_port
    finally:
        if container_id:
            res = subprocess.run(
                ["docker", "stop", container_id], capture_output=True, text=True, timeout=60
            )
            if res.returncode != 0:
                pytest.fail(
                    f"Docker stop returned non-zero exit code: {res.returncode}\n"
                    f"Stdout: {res.stdout}\nStderr: {res.stderr}"
                )
            res = subprocess.run(
                ["docker", "rm", container_id], capture_output=True, text=True, timeout=60
            )


def _seed_graphite_data(carbon_port: int):
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
    throughput_path = "performance-tests.daily.my-product.client.throughput"
    throughput_values = [56950, 57980, 57123, 60960, 60160, 61160]

    p50_path = "performance-tests.daily.my-product.client.p50"
    p50_values = [85, 87, 88, 89, 85, 87]

    cpu_path = "performance-tests.daily.my-product.server.cpu"
    cpu_values = [0.7, 0.9, 0.8, 0.1, 0.3, 0.2]

    start_timestamp = int(time.time())
    num_points = len(throughput_values)

    for i in range(num_points):
        # Data is sent from newest to oldest (same as datagen.sh)
        timestamp = start_timestamp - (i * 60)
        _send_to_graphite(carbon_port, throughput_path, throughput_values[i], timestamp)
        _send_to_graphite(carbon_port, p50_path, p50_values[i], timestamp)
        _send_to_graphite(carbon_port, cpu_path, cpu_values[i], timestamp)


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


def _remove_trailing_whitespaces(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines())
