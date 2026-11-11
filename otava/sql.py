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

import ast
import re
from string import Formatter
from typing import Any, List, Mapping, Sequence, Tuple

# Opaque tokens must be consumed before looking for string literals inside them.
_OPAQUE = r'--[^\n]*|/\*.*?\*/'
_POSTGRES_TOKENS = re.compile(
    _OPAQUE + r'''|"(?:""|[^"])*"|(?P<string>(?P<prefix>[eE])?'(?(prefix)(?:\\.|''|[^'\\])*|(?:''|[^'])*)')''',
    re.DOTALL,
)
_BIGQUERY_TOKENS = re.compile(
    _OPAQUE + r"|`(?:\\.|[^`\\])*`|(?P<string>(?P<prefix>[rR])?"
    r"(?P<quote>'''|\"\"\"|'|\")(?:\\.|(?!(?P=quote)).)*?(?P=quote))",
    re.DOTALL,
)
_ESCAPE = re.compile(r"\\([0-7]{1,3}|x[0-9a-fA-F]{1,2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|.)", re.DOTALL)


def _decode_escapes(value, dialect):
    escapes = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
    if dialect == "bigquery":
        escapes.update({"a": "\a", "v": "\v"})

    def decode(match):
        code = match.group(1)
        if code[0] in "01234567":
            return chr(int(code, 8))
        if code[0] in "xuU" and len(code) > 1:
            return chr(int(code[1:], 16))
        if code in escapes:
            return escapes[code]
        if dialect == "bigquery" and code not in "\\'\"`?":
            raise ValueError("Invalid BigQuery string escape: " + match.group())
        return code

    return _ESCAPE.sub(decode, value)


_CHANGE_FIELDS = ("forward_change_percent", "backward_change_percent", "p_value")


def parameterize_update_statement(
    statement: str,
    metric: str,
    values: Mapping[str, Any],
    changes: Sequence[Any],
    dialect: str = "postgres",
) -> Tuple[str, List[Any]]:
    """Bind values in legacy update templates without changing their syntax.

    Metric names remain SQL identifiers. Quoted template strings are bound as
    whole values, including any literal prefix or suffix around their fields.
    """
    if dialect not in ("postgres", "bigquery"):
        raise ValueError("Unsupported SQL dialect: " + dialect)
    parameters_by_name = dict(values)
    parameters_by_name.update(zip(_CHANGE_FIELDS, changes))
    positional_count = statement.count("%s")
    if positional_count:
        if positional_count != 3:
            raise ValueError("Update statement must contain exactly three %s placeholders")
        for name in _CHANGE_FIELDS:
            statement = statement.replace("%s", "{" + name + "}", 1)

    formatter = Formatter()
    parameters = []
    fields_by_name = {**parameters_by_name, "metric": metric}

    def render_unquoted(fragment):
        parts = []
        for literal, name, format_spec, conversion in formatter.parse(fragment):
            parts.append(literal)
            if name is None:
                continue
            value, _ = formatter.get_field(name, (), fields_by_name)
            repr_string = name != "metric" and isinstance(value, str) and conversion in ("r", "a")
            if conversion:
                value = formatter.convert_field(value, conversion)
            if format_spec:
                format_spec = formatter.vformat(format_spec, (), fields_by_name)
                value = formatter.format_field(value, format_spec)
            if repr_string:
                # repr/ascii supply SQL quotes in legacy unquoted fields. Bind
                # their logical contents, never those quote characters or SQL.
                value = ast.literal_eval(value.strip())
            if name == "metric":
                parts.append(str(value))
            else:
                parts.append("%s")
                parameters.append(value)
        return "".join(parts)

    parts = []
    start = 0
    tokens = _BIGQUERY_TOKENS if dialect == "bigquery" else _POSTGRES_TOKENS
    for match in tokens.finditer(statement):
        parts.append(render_unquoted(statement[start:match.start()]))
        if match.group("string") is None:
            parts.append(render_unquoted(match.group()))
            start = match.end()
            continue
        prefix = match.group("prefix") or ""
        quote = match.group("quote") if dialect == "bigquery" else "'"
        literal = match.group("string")[len(prefix) + len(quote):-len(quote)]
        if dialect == "postgres":
            literal = literal.replace("''", "'")
        if prefix.lower() == "e" or (dialect == "bigquery" and not prefix):
            literal = _decode_escapes(literal, dialect)
        fields = list(formatter.parse(literal))
        if any(name is not None for _, name, _, _ in fields):
            parameters.append(formatter.vformat(literal, (), fields_by_name))
            parts.append("%s")
        else:
            parts.append(match.group())
        start = match.end()
    parts.append(render_unquoted(statement[start:]))
    return "".join(parts), parameters
