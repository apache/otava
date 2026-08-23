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
import tempfile
import textwrap
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import otava.series
from otava.main import script_main


class CliOptionsTest(unittest.TestCase):

    # Test --deterministic-edivisive in various ways
    def test_no_cli_option(self):
        with patch('otava.series.compute_change_points') as mock_split:
            script_main(args=[])
            mock_split.assert_not_called()

    def test_default_cli_option(self):
        with patch('otava.series.compute_change_points') as mock_split:
            mock_split.return_value = ([], [])
            with tempfile.TemporaryDirectory() as td:
                td_path = Path(td)
                csv_path, timestamps, config_path, test_name = _create_files_in_temp_dir(td_path)
                # _uv_run(td_path, test_name)
                config_path_str = "" + str(config_path)
                script_main(args=["analyze", "--config", config_path_str, test_name])

            assert otava.series.compute_change_points.call_count == 2

    # Failing due to lack of cp.metric see pull#141
    # def test_orig_cli_option(self):
    #     with patch('otava.series.compute_change_points') as mock_orig:
    #         mock_orig.return_value = ([], None)
    #         with tempfile.TemporaryDirectory() as td:
    #             td_path = Path(td)
    #             csv_path, timestamps, config_path, test_name = _create_files_in_temp_dir(td_path)
    #             # _uv_run(td_path, test_name)
    #             config_path_str = "" + str(config_path)
    #             script_main(args=["analyze", "--config", config_path_str, "--orig-edivisive", "true", test_name])
    #
    #         assert otava.series.compute_change_points_orig.call_count == 2


def _create_files_in_temp_dir(td_path: Path):
    data_dir = td_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    csv_path, timestamps = _create_csv_data_file_for_test(td_path)
    config_path, test_name = _create_csv_config_file_for_test(td_path)

    return csv_path, timestamps, config_path, test_name


def _create_csv_data_file_for_test(td_path: Path):
    # create data directory and write CSV
    data_dir = td_path / "data"
    csv_path = data_dir / "local_sample.csv"

    # Generate some CSV content
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

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["time", "commit", "metric1", "metric2"])
        writer.writerows(data_points)

    return csv_path, timestamps


def _create_csv_config_file_for_test(td_path: Path):
    data_dir = td_path / "data"
    csv_path = str(data_dir / "local_sample.csv")

    config_content = textwrap.dedent(
        """\
        tests:
            sample_for_test:
                type: csv
                file: """ + csv_path + """
                time_column: time
                attributes: [commit]
                metrics: [metric1, metric2]
                csv_options:
                    delimiter: ","
                    quote_char: "'"
        """
    )
    config_path = td_path / "otava.yaml"
    config_path.write_text(config_content, encoding="utf-8")
    return config_path, "sample_for_test"
