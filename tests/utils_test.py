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

from datetime import datetime, timezone

import pytest

from otava.util import clean_str, parse_datetime


def test_clean_str_none():
    assert clean_str(None) is None


def test_clean_str_empty_string():
    assert clean_str("") is None


@pytest.mark.parametrize("value", ["null", "NULL", "NuLl"])
def test_clean_str_null_variants(value):
    assert clean_str(value) is None


@pytest.mark.parametrize("value", [" ", "   ", "\t", "\n", "\r\n"])
def test_clean_str_whitespace_only(value):
    assert clean_str(value) is None


@pytest.mark.parametrize("value", [
    "abc",
    "commit123",
    "new-feature",
    "v1.0.0",
])
def test_clean_str_valid_strings(value):
    assert clean_str(value) == value


@pytest.mark.parametrize("value,expected", [
    ("  abc  ", "abc"),
    (" null ", None),
    ("NULL", None),
    ("   ", None),
])
def test_clean_str_mixed_cases(value, expected):
    assert clean_str(value) == expected


def test_clean_str_non_string_input():
    assert clean_str(123) == 123
    assert clean_str(0) == 0
    assert clean_str(False) is False



def test_parse_datetime_none():
    assert parse_datetime(None) is None


def test_parse_datetime_pass_through_datetime():
    dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert parse_datetime(dt) == dt


def test_parse_datetime_timestamp_int():
    ts = 1700000000
    result = parse_datetime(ts)

    assert isinstance(result, datetime)
    assert result.tzinfo is not None  # ensures timezone-aware


def test_parse_datetime_string():
    result = parse_datetime("2024-01-01 10:00:00")

    assert isinstance(result, datetime)
    assert result.tzinfo is not None


def test_parse_datetime_invalid_type():
    with pytest.raises(TypeError):
        parse_datetime(["bad input"])