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

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from otava.postgres import Postgres


@pytest.mark.parametrize("predicate, attribute, bound", [
    ("name = '{name}'", "O'Reilly", "O'Reilly"),
    ("name = '{name}'", "x' OR 1=1 --", "x' OR 1=1 --"),
    ("name = 'prefix-{name}'", "O'Reilly", "prefix-O'Reilly"),
    ("name = {name}", 42, 42),
])
def test_legacy_update_binds_attributes(predicate, attribute, bound):
    connection = Mock()
    backend = Postgres(None)
    backend._Postgres__conn = connection
    point = SimpleNamespace(time=0, stats=SimpleNamespace(pvalue=.01),
                            forward_change_percent=lambda: 10.,
                            backward_change_percent=lambda: -9.)
    config = SimpleNamespace(time_column="time", update_stmt=(
        "UPDATE results SET {metric}_forward=%s, {metric}_backward=%s, "
        "{metric}_p=%s WHERE " + predicate))

    backend.insert_change_point(config, "speed", {"name": attribute}, point)

    statement, parameters = connection.cursor.return_value.execute.call_args.args
    assert statement == ("UPDATE results SET speed_forward=%s, speed_backward=%s, "
                         "speed_p=%s WHERE name = %s")
    assert list(parameters) == [10., -9., .01, bound]
    connection.commit.assert_called_once()


def test_legacy_named_changes_bind_as_values():
    connection = Mock()
    backend = Postgres(None)
    backend._Postgres__conn = connection
    point = SimpleNamespace(time=0, stats=SimpleNamespace(pvalue=.01),
                            forward_change_percent=lambda: 10.,
                            backward_change_percent=lambda: -9.)
    config = SimpleNamespace(time_column="time", update_stmt=(
        "UPDATE results SET {metric}_forward={forward_change_percent}, "
        "{metric}_p={p_value} WHERE name = '{name}'"))
    backend.insert_change_point(config, "speed", {"name": "O'Reilly"}, point)
    statement, parameters = connection.cursor.return_value.execute.call_args.args
    assert statement == "UPDATE results SET speed_forward=%s, speed_p=%s WHERE name = %s"
    assert list(parameters) == [10., .01, "O'Reilly"]


@pytest.mark.parametrize("quote", ["'", '"'])
def test_bigquery_preserves_named_update_template(monkeypatch, quote):
    from otava.bigquery import BigQuery

    connection = Mock()
    monkeypatch.setattr("otava.bigquery.dbapi.Connection", Mock(return_value=connection))
    backend = BigQuery(None)
    backend._BigQuery__client = Mock()
    point = SimpleNamespace(time=0, stats=SimpleNamespace(pvalue=.01),
                            forward_change_percent=lambda: 10.,
                            backward_change_percent=lambda: -9.)
    config = SimpleNamespace(time_column="time", update_stmt=(
        "UPDATE results SET {metric}_forward={forward_change_percent}, "
        "{metric}_p={p_value} WHERE name = " + quote + "{name}" + quote))

    backend.insert_change_point(config, "speed", {"name": "x' OR 1=1 --"}, point)

    statement, parameters = connection.cursor.return_value.execute.call_args.args
    assert statement == "UPDATE results SET speed_forward=%s, speed_p=%s WHERE name = %s"
    assert list(parameters) == [10., .01, "x' OR 1=1 --"]


@pytest.mark.parametrize("conversion", ["r", "a"])
@pytest.mark.parametrize("value", ["alice", "café", "O'Reilly", "x' OR 1=1 --", 'x" OR 1=1 --'])
def test_unquoted_repr_binds_logical_string(conversion, value):
    from otava.sql import parameterize_update_statement

    statement, parameters = parameterize_update_statement(
        "UPDATE t SET v={p_value} WHERE name={name!" + conversion + "}",
        "speed", {"name": value}, [1, 2, .01],
    )
    assert statement == "UPDATE t SET v=%s WHERE name=%s"
    assert parameters == [.01, value]


def test_field_access_and_nested_format_specs():
    from otava.sql import parameterize_update_statement

    statement, parameters = parameterize_update_statement(
        "UPDATE t SET v={point.value:.{precision}f} WHERE name={names[0]!r}",
        "speed", {"point": SimpleNamespace(value=1.234), "precision": 2,
                  "names": ["O'Reilly"]}, [1, 2, .01],
    )
    assert statement == "UPDATE t SET v=%s WHERE name=%s"
    assert parameters == ["1.23", "O'Reilly"]


@pytest.mark.parametrize("literal, expected", [
    ("E'{name}'", "O'Reilly"),
    (r"E'prefix\n{name}'", "prefix\nO'Reilly"),
    (r"E'\a\v{name}'", "avO'Reilly"),
    (r"E'it\'s {name}'", "it's O'Reilly"),
    ("'it''s {name}'", "it's O'Reilly"),
])
def test_postgres_string_literals(literal, expected):
    from pg8000.dbapi import convert_paramstyle

    from otava.sql import parameterize_update_statement

    statement, parameters = parameterize_update_statement(
        "UPDATE t SET v={p_value} WHERE name=" + literal,
        "speed", {"name": "O'Reilly"}, [1, 2, .01],
    )
    assert statement == "UPDATE t SET v=%s WHERE name=%s"
    assert parameters == [.01, expected]
    assert convert_paramstyle("format", statement, parameters)[0] == (
        "UPDATE t SET v=$1 WHERE name=$2"
    )


@pytest.mark.parametrize("literal, expected", [
    ('"{name}"', "O'Reilly"),
    (r'''"say \"hi\" {name}"''', 'say "hi" O\'Reilly'),
    (r"'it\'s {name}'", "it's O'Reilly"),
    ('"""hello\n{name}"""', "hello\nO'Reilly"),
    (r'''r"path\n{name}"''', r"path\nO'Reilly"),
    ("R'''path\\n{name}'''", r"path\nO'Reilly"),
])
def test_bigquery_string_literals(literal, expected):
    from google.cloud.bigquery.dbapi.cursor import _format_operation

    from otava.sql import parameterize_update_statement

    statement, parameters = parameterize_update_statement(
        "UPDATE t SET v={p_value} WHERE name=" + literal,
        "speed", {"name": "O'Reilly"}, [1, 2, .01], dialect="bigquery",
    )
    assert statement == "UPDATE t SET v=%s WHERE name=%s"
    assert parameters == [.01, expected]
    assert _format_operation(statement, parameters)[0] == "UPDATE t SET v=? WHERE name=?"


def test_literal_escapes_do_not_decode_attribute_data():
    from otava.sql import parameterize_update_statement

    payload = r"\n' OR 1=1 --"
    statement, parameters = parameterize_update_statement(
        r"UPDATE t SET v={p_value} WHERE name=E'prefix\n{name}'",
        "speed", {"name": payload}, [1, 2, .01],
    )
    assert statement == "UPDATE t SET v=%s WHERE name=%s"
    assert parameters == [.01, "prefix\n" + payload]
