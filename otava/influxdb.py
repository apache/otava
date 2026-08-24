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

from dataclasses import dataclass

from influxdb_client_3 import InfluxDBClient3


@dataclass
class InfluxDBConfig:
    NAME = "influxdb"

    host: str
    database: str
    token: str

    @staticmethod
    def add_parser_args(arg_group):
        arg_group.add_argument("--influxdb-host", help="InfluxDB 3 server URL", env_var="INFLUXDB_HOST")
        arg_group.add_argument("--influxdb-database", help="InfluxDB 3 database name", env_var="INFLUXDB_DATABASE")
        arg_group.add_argument("--influxdb-token", help="InfluxDB 3 database token", env_var="INFLUXDB_TOKEN")

    @staticmethod
    def from_parser_args(args):
        return InfluxDBConfig(
            host=getattr(args, "influxdb_host", None),
            database=getattr(args, "influxdb_database", None),
            token=getattr(args, "influxdb_token", None),
        )


class InfluxDB:
    def __init__(self, config: InfluxDBConfig):
        self.config = config
        self._client = None

    @property
    def client(self) -> InfluxDBClient3:
        if self._client is None:
            self._client = InfluxDBClient3(
                host=self.config.host,
                database=self.config.database,
                token=self.config.token,
            )
        return self._client

    def fetch_data(self, query: str, language: str):
        table = self.client.query(query=query, language=language)
        columns = table.column_names
        # Keep the public result contract consistent with the SQL importers:
        # rows are positional tuples in the same order as ``columns``.
        rows = [tuple(record[column] for column in columns) for record in table.to_pylist()]
        return columns, rows
