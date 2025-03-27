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

import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

import pytz


@dataclass
class DataSelector:
    branch: Optional[str]
    metrics: Optional[List[str]]
    attributes: Optional[List[str]]
    last_n_points: int
    since_commit: Optional[str]
    since_version: Optional[str]
    since_time: datetime
    until_commit: Optional[str]
    until_version: Optional[str]
    until_time: datetime

    def __init__(self):
        self.branch = None
        self.metrics = None
        self.attributes = None
        self.last_n_points = sys.maxsize
        self.since_commit = None
        self.since_version = None
        self.since_time = datetime.now(tz=pytz.UTC) - timedelta(days=365)
        self.until_commit = None
        self.until_version = None
        self.until_time = datetime.now(tz=pytz.UTC)

    def get_selection_description(self):
        attributes = "\n".join(
            [f"{a}: {v}" for a, v in self.__dict__.items() if not a.startswith("__") and v]
        )
        return f"Data Selection\n{attributes}"
