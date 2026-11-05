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

from collections import OrderedDict
from enum import Enum, unique
from typing import List

from tabulate import tabulate

from otava.change_point_divisive.base import ChangePoints
from otava.series import Series
from otava.util import format_timestamp, insert_multiple, remove_common_prefix


@unique
class ReportType(Enum):
    LOG = "log"
    JSON = "json"
    REGRESSIONS_ONLY = "regressions_only"

    def __str__(self):
        return self.value


class Report:
    __series: Series
    __change_points: ChangePoints

    def __init__(self, series: Series, change_points: ChangePoints):
        self.__series = series
        self.__change_points = change_points

    @staticmethod
    def __column_widths(log: List[str]) -> List[int]:
        return [len(c) for c in log[1].split(None)]

    def produce_report(self, test_name: str, report_type: ReportType):
        if report_type == ReportType.LOG:
            return self.__format_log_annotated(test_name)
        elif report_type == ReportType.JSON:
            return self.__format_json(test_name)
        elif report_type == ReportType.REGRESSIONS_ONLY:
            return self.__format_regressions_only(test_name)
        else:
            from otava.main import OtavaError

            raise OtavaError(f"Unknown report type: {report_type}")

    def __format_log(self) -> str:
        time_column = [format_timestamp(ts) for ts in self.__series.time]
        table = {"time": time_column, **self.__series.attributes, **self.__series.data}
        metrics = list(self.__series.data.keys())
        headers = list(
            OrderedDict.fromkeys(
                ["time", *self.__series.attributes, *remove_common_prefix(metrics)]
            )
        )
        return tabulate(table, headers=headers)

    def __format_log_annotated(self, test_name: str) -> str:
        """Returns test log with change points marked as horizontal lines"""
        lines = self.__format_log().split("\n")
        col_widths = self.__column_widths(lines)
        indexes = [list(cpg.changes.values())[0].index for cpg in self.__change_points]
        separators = []
        columns = list(
            OrderedDict.fromkeys(["time", *self.__series.attributes, *self.__series.data])
        )
        for cpg in self.__change_points:
            separator = ""
            info = ""
            for col_index, col_name in enumerate(columns):
                col_width = col_widths[col_index]
                change = [c for m, c in cpg.changes.items() if m == col_name]
                if change:
                    change_percent = change[0].forward_change_percent()
                    separator += "·" * col_width + "  "
                    info += f"{change_percent:+.1f}%".rjust(col_width) + "  "
                else:
                    separator += " " * (col_width + 2)
                    info += " " * (col_width + 2)

            separators.append(f"{separator}\n{info}\n{separator}")

        lines = lines[:2] + insert_multiple(lines[2:], separators, indexes)
        return "\n".join(lines)

    def __format_json(self, test_name: str) -> str:
        import json

        return json.dumps(
            {
                test_name: [
                    self.__format_change_point_group_json(cpg) for cpg in self.__change_points
                ]
            }
        )

    @staticmethod
    def __format_change_point_group_json(cpg):
        return {
            "time": cpg.time,
            "attributes": cpg.attributes,
            "changes": [Report.__format_change_point_json(cp) for cp in cpg.changes.values()],
        }

    @staticmethod
    def __format_change_point_json(cp):
        return {
            "metric": cp.metric,
            "index": int(cp.index),
            "forward_change_percent": f"{cp.forward_change_percent():.0f}",
            "backward_change_percent": f"{cp.backward_change_percent():.0f}",
            "magnitude": f"{cp.magnitude():.6f}",
            "mean_before": f"{cp.stats.mean_before():.6f}",
            "stddev_before": f"{cp.stats.stddev_before():.6f}",
            "mean_after": f"{cp.stats.mean_after():.6f}",
            "stddev_after": f"{cp.stats.stddev_after():.6f}",
            "pvalue": f"{cp.stats.pvalue:.6f}",
        }

    def __format_regressions_only(self, test_name: str) -> str:
        output = []
        for cpg in self.__change_points:
            regressions = []
            for metric_name, cp in cpg.changes.items():
                metric = self.__series.metrics[metric_name]
                if metric.direction * cp.forward_change_percent() < 0:
                    regressions.append(
                        (
                            cp.metric,
                            cp.stats.mean_1,
                            cp.stats.mean_2,
                            cp.stats.forward_rel_change() * 100.0,
                        )
                    )

            if regressions:
                output.append(format_timestamp(cpg.time))
                output.extend(
                    [
                        "    {:16}:\t{:#8.3g}\t--> {:#8.3g}\t({:+6.1f}%)".format(*args)
                        for args in regressions
                    ]
                )

        if output:
            return f"Regressions in {test_name}:" + "\n" + "\n".join(output)
        else:
            return f"No regressions found in {test_name}."
