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

import shutil
import socket
import subprocess
import time
from contextlib import contextmanager
from typing import Callable

import pytest


@contextmanager
def container(
    image: str,
    *,
    env: dict[str, str] | None = None,
    ports: list[int] | None = None,
    volumes: dict[str, str] | None = None,
    readiness_check: Callable[[str, dict[int, int]], bool] | None = None,
):
    """
    Generic context manager for running a Docker container.

    Args:
        image: Docker image to run (e.g., "postgres:latest").
        env: Optional dict of environment variables to set in the container.
        ports: Optional list of container ports to publish (will be mapped to random host ports).
        volumes: Optional dict mapping host paths to container paths for volume mounts.
        readiness_check: Optional callable that takes (container_id, port_map) and returns True
                         when the container is ready. port_map maps container ports to host ports.
                         If not provided, the container is considered ready once all ports accept
                         TCP connections.

    Yields:
        A tuple of (container_id, port_map) where port_map is a dict mapping container ports
        to their assigned host ports.
    """
    if not shutil.which("docker"):
        pytest.fail("docker is not available on PATH")

    container_id = None
    try:
        # Build docker run command
        cmd = ["docker", "run", "-d"]

        # Add environment variables
        if env:
            for key, value in env.items():
                cmd.extend(["--env", f"{key}={value}"])

        # Add volume mounts
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["--volume", f"{host_path}:{container_path}"])

        # Add port mappings
        if ports:
            for port in ports:
                cmd.extend(["--publish", str(port)])

        cmd.append(image)

        # Start the container
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

        # Get assigned host ports for each container port
        port_map: dict[int, int] = {}
        if ports:
            for port in ports:
                inspect_cmd = [
                    "docker",
                    "inspect",
                    "-f",
                    f'{{{{ (index (index .NetworkSettings.Ports "{port}/tcp") 0).HostPort }}}}',
                    container_id,
                ]
                inspect_proc = subprocess.run(
                    inspect_cmd, capture_output=True, text=True, timeout=60
                )
                if inspect_proc.returncode != 0:
                    pytest.fail(
                        "Docker inspect returned non-zero exit code.\n\n"
                        f"Command: {inspect_cmd!r}\n"
                        f"Exit code: {inspect_proc.returncode}\n\n"
                        f"Stdout:\n{inspect_proc.stdout}\n\n"
                        f"Stderr:\n{inspect_proc.stderr}\n"
                    )
                port_map[port] = int(inspect_proc.stdout.strip())

        # Wait for readiness
        deadline = time.time() + 60
        ready = False
        while time.time() < deadline:
            # First check that all ports accept TCP connections
            all_ports_ready = True
            for host_port in port_map.values():
                try:
                    with socket.create_connection(("localhost", host_port), timeout=1):
                        pass
                except OSError:
                    all_ports_ready = False
                    break

            if not all_ports_ready:
                time.sleep(1)
                continue

            # If a custom readiness check is provided, use it
            if readiness_check is not None:
                if readiness_check(container_id, port_map):
                    ready = True
                    break
                time.sleep(1)
            else:
                # No custom check, ports being open is sufficient
                ready = True
                break

        if not ready:
            pytest.fail("Container did not become ready within timeout.")

        yield container_id, port_map
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
            subprocess.run(
                ["docker", "rm", container_id], capture_output=True, text=True, timeout=60
            )


@contextmanager
def graphite_container():
    """
    Context manager for running a Graphite container with seeded data.
    Yields the Graphite HTTP port and ensures cleanup on exit.
    """
    with container(
        "graphiteapp/graphite-statsd",
        ports=[80, 2003],
    ) as (container_id, port_map):
        yield str(port_map[80])


def _remove_trailing_whitespaces(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines())
