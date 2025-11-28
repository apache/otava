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
from datetime import datetime
from typing import Dict

import pg8000

from otava.analysis import ChangePoint
from otava.test_config import PostgresTestConfig


@dataclass
class PostgresConfig:
    hostname: str
    port: int
    username: str
    password: str
    database: str


@dataclass
class PostgresError(Exception):
    message: str


class Postgres:
    __conn = None
    __config = None

    def __init__(self, config: PostgresConfig):
        self.__config = config

    def __get_conn(self) -> pg8000.dbapi.Connection:
        if self.__conn is None:
            self.__conn = pg8000.dbapi.Connection(
                host=self.__config.hostname,
                port=self.__config.port,
                user=self.__config.username,
                password=self.__config.password,
                database=self.__config.database,
            )
        return self.__conn

    def fetch_data(self, query: str):
        cursor = self.__get_conn().cursor()
        cursor.execute(query)
        columns = [c[0] for c in cursor.description]
        return (columns, cursor.fetchall())

    def insert_change_point(
        self,
        test: PostgresTestConfig,
        metric_name: str,
        attributes: Dict,
        change_point: ChangePoint,
    ):
        cursor = self.__get_conn().cursor()
        kwargs = {**attributes, **{test.time_column: datetime.utcfromtimestamp(change_point.time)}}
        update_stmt = test.update_stmt.format(metric=metric_name, **kwargs)
        cursor.execute(
            update_stmt,
            (
                change_point.forward_change_percent(),
                change_point.backward_change_percent(),
                change_point.stats.pvalue,
            ),
        )
        self.__get_conn().commit()
