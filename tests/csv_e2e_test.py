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
from e2e_test_utils import _remove_trailing_whitespaces


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

        assert _remove_trailing_whitespaces(proc.stdout) == expected_output.rstrip("\n")


def test_analyze_csv_multiple_branches_without_branch_flag_fails():
    """
    E2E test: CSV with multiple branches but no --branch flag should fail.
    """
    now = datetime.now()
    data_points = [
        (now - timedelta(days=4), "aaa0", "main", 154023, 10.43),
        (now - timedelta(days=3), "aaa1", "main", 138455, 10.23),
        (now - timedelta(days=2), "aaa2", "feature-x", 143112, 10.29),
        (now - timedelta(days=1), "aaa3", "feature-x", 149190, 10.91),
        (now, "aaa4", "main", 132098, 10.34),
    ]

    config_content = textwrap.dedent(
        """\
        tests:
          local.sample:
            type: csv
            file: data/local_sample.csv
            time_column: time
            attributes: [commit, branch]
            metrics: [metric1, metric2]
        """
    )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        data_dir = td_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / "local_sample.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "commit", "branch", "metric1", "metric2"])
            for ts, commit, branch, m1, m2 in data_points:
                writer.writerow([ts.strftime("%Y.%m.%d %H:%M:%S %z"), commit, branch, m1, m2])

        config_path = td_path / "otava.yaml"
        config_path.write_text(config_content, encoding="utf-8")

        cmd = ["uv", "run", "otava", "analyze", "local.sample"]
        proc = subprocess.run(
            cmd,
            cwd=str(td_path),
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ, OTAVA_CONFIG=str(config_path)),
        )

        output = proc.stderr + proc.stdout
        assert "multiple branches" in output
        assert "--branch" in output
        assert "main" in output
        assert "feature-x" in output


def test_analyze_csv_branch_flag_without_branch_column_fails():
    """
    E2E test: --branch flag specified but CSV has no branch column should fail.
    """
    now = datetime.now()
    data_points = [
        (now - timedelta(days=2), "aaa0", 154023, 10.43),
        (now - timedelta(days=1), "aaa1", 138455, 10.23),
        (now, "aaa2", 143112, 10.29),
    ]

    config_content = textwrap.dedent(
        """\
        tests:
          local.sample:
            type: csv
            file: data/local_sample.csv
            time_column: time
            attributes: [commit]
            metrics: [metric1, metric2]
        """
    )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        data_dir = td_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / "local_sample.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "commit", "metric1", "metric2"])
            for ts, commit, m1, m2 in data_points:
                writer.writerow([ts.strftime("%Y.%m.%d %H:%M:%S %z"), commit, m1, m2])

        config_path = td_path / "otava.yaml"
        config_path.write_text(config_content, encoding="utf-8")

        cmd = ["uv", "run", "otava", "analyze", "local.sample", "--branch", "main"]
        proc = subprocess.run(
            cmd,
            cwd=str(td_path),
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ, OTAVA_CONFIG=str(config_path)),
        )

        output = proc.stderr + proc.stdout
        assert "--branch was specified" in output
        assert "branch" in output and "column" in output


def test_analyze_csv_with_branch_filter():
    """
    E2E test: --branch flag filters CSV rows correctly.
    """
    now = datetime.now()
    # Data with change point in feature-x branch
    data_points = [
        # main branch - no change point
        (now - timedelta(days=7), "aaa0", "main", 100, 10.0),
        (now - timedelta(days=6), "aaa1", "main", 102, 10.1),
        (now - timedelta(days=5), "aaa2", "main", 101, 10.0),
        (now - timedelta(days=4), "aaa3", "main", 103, 10.2),
        # feature-x branch - has a change point
        (now - timedelta(days=7), "bbb0", "feature-x", 100, 10.0),
        (now - timedelta(days=6), "bbb1", "feature-x", 102, 10.1),
        (now - timedelta(days=5), "bbb2", "feature-x", 101, 10.0),
        (now - timedelta(days=4), "bbb3", "feature-x", 150, 15.0),  # regression
        (now - timedelta(days=3), "bbb4", "feature-x", 152, 15.2),
        (now - timedelta(days=2), "bbb5", "feature-x", 148, 14.8),
    ]

    config_content = textwrap.dedent(
        """\
        tests:
          local.sample:
            type: csv
            file: data/local_sample.csv
            time_column: time
            attributes: [commit, branch]
            metrics: [metric1, metric2]
        """
    )

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        data_dir = td_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        csv_path = data_dir / "local_sample.csv"
        with open(csv_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["time", "commit", "branch", "metric1", "metric2"])
            for ts, commit, branch, m1, m2 in data_points:
                writer.writerow([ts.strftime("%Y.%m.%d %H:%M:%S %z"), commit, branch, m1, m2])

        config_path = td_path / "otava.yaml"
        config_path.write_text(config_content, encoding="utf-8")

        # Analyze feature-x branch - should show change point
        cmd = ["uv", "run", "otava", "analyze", "local.sample", "--branch", "feature-x"]
        proc = subprocess.run(
            cmd,
            cwd=str(td_path),
            capture_output=True,
            text=True,
            timeout=120,
            env=dict(os.environ, OTAVA_CONFIG=str(config_path)),
        )

        if proc.returncode != 0:
            pytest.fail(
                "Command returned non-zero exit code.\n\n"
                f"Command: {cmd!r}\n"
                f"Exit code: {proc.returncode}\n\n"
                f"Stdout:\n{proc.stdout}\n\n"
                f"Stderr:\n{proc.stderr}\n"
            )

        output = proc.stdout
        # Should only show feature-x data (bbb commits)
        assert "bbb" in output
        # Should NOT show main branch data (aaa commits)
        assert "aaa" not in output
        # Should show a change point (increase ~50%)
        assert "+" in output and "%" in output
