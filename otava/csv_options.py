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

import enum
from dataclasses import dataclass
from typing import Optional

import configargparse


def single_character(value: str) -> str:
    """The csv module only accepts single-character delimiters and quote characters."""
    if len(value) != 1:
        raise configargparse.ArgumentTypeError(f"must be a single character, got {value!r}")
    return value


@dataclass
class CsvConfig:
    NAME = "csv"

    delimiter: Optional[str] = None
    quote_char: Optional[str] = None

    @staticmethod
    def add_parser_args(arg_group):
        arg_group.add_argument(
            "--csv-delimiter",
            help="CSV delimiter",
            env_var="CSV_DELIMITER",
            type=single_character,
            default=configargparse.SUPPRESS,
        )
        arg_group.add_argument(
            "--csv-quote-char",
            help="CSV quote character",
            env_var="CSV_QUOTE_CHAR",
            type=single_character,
            default=configargparse.SUPPRESS,
        )

    @staticmethod
    def from_parser_args(args):
        return CsvConfig(
            delimiter=getattr(args, "csv_delimiter", None),
            quote_char=getattr(args, "csv_quote_char", None),
        )


@dataclass
class CsvOptions:
    delimiter: str
    quote_char: str

    def __init__(self):
        self.delimiter = ","
        self.quote_char = '"'


class CsvColumnType(enum.Enum):
    Numeric = 1
    DateTime = 2
    Str = 3
