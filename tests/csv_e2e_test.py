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

import csv
import os
import subprocess
import tempfile
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def test_analyze_csv():
    """
    End-to-end test for the CSV example from docs/CSV.md.

    Writes a temporary CSV and otava.yaml, runs:
      uv run otava analyze local.sample
    in the temporary directory, and compares stdout to the expected output.
    """

    now = datetime.now()
    n = 10
    timestamps = [now - timedelta(days=i) for i in range(n)]
    metrics1 = [154023, 138455, 143112, 149190, 132098, 151344, 155145, 148889, 149466, 148209]
    metrics2 = [10.43, 10.23, 10.29, 10.91, 10.34, 10.69, 9.23, 9.11, 9.13, 9.03]
    data_points = []
    for i in range(n):
        data_points.append(
            (
                timestamps[i].strftime("%Y.%m.%d %H:%M:%S %z"),  # time
                "aaa" + str(i),  # commit
                metrics1[i],
                metrics2[i],
            )
        )

    config_content = textwrap.dedent(
        """\
        tests:
          local.sample:
            type: csv
            file: data/local_sample.csv
            time_column: time
            attributes: [commit]
            metrics: [metric1, metric2]
            csv_options:
              delimiter: ","
              quotechar: "'"
        """
    )
    expected_output = textwrap.dedent(
        """\
        time                       commit      metric1    metric2
        -------------------------  --------  ---------  ---------
        {}  aaa0         154023      10.43
        {}  aaa1         138455      10.23
        {}  aaa2         143112      10.29
        {}  aaa3         149190      10.91
        {}  aaa4         132098      10.34
        {}  aaa5         151344      10.69
                                                        ·········
                                                           -12.9%
                                                        ·········
        {}  aaa6         155145       9.23
        {}  aaa7         148889       9.11
        {}  aaa8         149466       9.13
        {}  aaa9         148209       9.03
        """.format(
            *[ts.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S +0000") for ts in timestamps]
        )
    )
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # create data directory and write CSV
        data_dir = td_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / "local_sample.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "commit", "metric1", "metric2"])
            writer.writerows(data_points)

        # write otava.yaml in temp cwd
        config_path = td_path / "otava.yaml"
        config_path.write_text(config_content, encoding="utf-8")

        # run command
        cmd = ["uv", "run", "otava", "analyze", "local.sample"]
        proc = subprocess.run(
            cmd,
            cwd=str(td_path),
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ, OTAVA_CONFIG=config_path),
        )

        if proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {cmd!r}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"Stdout:\n{proc.stdout}\n\n"
                f"Stderr:\n{proc.stderr}\n"
            )

        # Python 3.9 and earlier does not print it for some reason...
        output_without_log = proc.stdout.replace(
            "Computing change points for test local.sample...", ""
        )
        # Python 3.9 complains about importlib.metadata.packages_distributions...
        output_without_log = output_without_log.replace(
            "An error occurred: module 'importlib.metadata' has no attribute 'packages_distributions'",
            "",
        )
        assert _remove_trailing_whitespaces(output_without_log) == expected_output.rstrip("\n")


def test_regressions_csv():
    """
    End-to-end test for the CSV example from docs/CSV.md.

    Writes a temporary CSV and otava.yaml, runs:
      uv run otava analyze local.sample
    in the temporary directory, and compares stdout to the expected output.
    """

    now = datetime.now()
    n = 10
    timestamps = [now - timedelta(days=i) for i in range(n)]
    metrics1 = [154023, 138455, 143112, 149190, 132098, 151344, 155145, 148889, 149466, 148209]
    metrics2 = [10.43, 10.23, 10.29, 10.91, 10.34, 10.69, 9.23, 9.11, 9.13, 9.03]
    data_points = []
    for i in range(n):
        data_points.append(
            (
                timestamps[i].strftime("%Y.%m.%d %H:%M:%S %z"),  # time
                "aaa" + str(i),  # commit
                metrics1[i],
                metrics2[i],
            )
        )

    config_content = textwrap.dedent(
        """\
        tests:
          local.sample:
            type: csv
            file: data/local_sample.csv
            time_column: time
            attributes: [commit]
            metrics: [metric1, metric2]
            csv_options:
              delimiter: ","
              quotechar: "'"
        """
    )
    expected_output = textwrap.dedent(
        """\
        local.sample:
            metric2         :     10.5 -->     9.12 ( -12.9%)
        Regressions in 1 test found
        """
    )
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # create data directory and write CSV
        data_dir = td_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / "local_sample.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "commit", "metric1", "metric2"])
            writer.writerows(data_points)

        # write otava.yaml in temp cwd
        config_path = td_path / "otava.yaml"
        config_path.write_text(config_content, encoding="utf-8")

        # run command
        cmd = ["uv", "run", "otava", "regressions", "local.sample"]
        proc = subprocess.run(
            cmd,
            cwd=str(td_path),
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ, OTAVA_CONFIG=config_path),
        )

        if proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {cmd!r}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"Stdout:\n{proc.stdout}\n\n"
                f"Stderr:\n{proc.stderr}\n"
            )

        # Python 3.9 and earlier does not print it for some reason...
        output_without_log = proc.stdout.replace(
            "Computing change points for test local.sample...", ""
        )
        # Python 3.9 complains about importlib.metadata.packages_distributions...
        output_without_log = output_without_log.replace(
            "An error occurred: module 'importlib.metadata' has no attribute 'packages_distributions'",
            "",
        )
        assert _remove_trailing_whitespaces(output_without_log) == expected_output.rstrip("\n")


def _remove_trailing_whitespaces(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.splitlines()).strip()
