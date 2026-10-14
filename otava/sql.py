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

from string import Formatter
from typing import Any, List, Mapping, Sequence, Tuple

_CHANGE_FIELDS = (
    "forward_change_percent",
    "backward_change_percent",
    "p_value",
)


def parameterize_update_statement(
    statement: str,
    metric: str,
    values: Mapping[str, Any],
    changes: Sequence[Any],
) -> Tuple[str, List[Any]]:
    """Build SQL and ordered parameters from an update template.

    The metric is inserted as an SQL identifier. Attribute and change-point
    values are returned separately for the database driver to bind.

    Example:
        Template:
            UPDATE results
            SET {metric}_forward=%s, {metric}_backward=%s, {metric}_p=%s
            WHERE experiment_id='{experiment_id}'

        With metric="latency", changes=(1.5, -1.4, 0.01), and
        values={"experiment_id": "exp-42"}, this returns:

            SQL: UPDATE results SET latency_forward=%s,
                 latency_backward=%s, latency_p=%s
                 WHERE experiment_id=%s
            Parameters: [1.5, -1.4, 0.01, "exp-42"]
    """
    if len(changes) != len(_CHANGE_FIELDS) or statement.count("%s") != len(
        _CHANGE_FIELDS
    ):
        raise ValueError("Update statement must contain exactly three %s placeholders")

    parameters_by_name = dict(values)
    parameters_by_name.update(zip(_CHANGE_FIELDS, changes))

    for name in parameters_by_name:
        statement = statement.replace("'{" + name + "}'", "{" + name + "}")
    for name in _CHANGE_FIELDS:
        statement = statement.replace("%s", "{" + name + "}", 1)

    formatter = Formatter()
    parts = []
    parameters = []
    for literal, field_name, format_spec, conversion in formatter.parse(statement):
        parts.append(literal)

        # Skip literal SQL text
        if field_name is None:
            continue

        # Reject formatted placeholders, e.g. {metric!s}
        if conversion or format_spec:
            raise ValueError(
                "Update statement placeholders cannot use formatting options"
            )

        # Insert the metric as a SQL identifier, e.g. a column name.
        if field_name == "metric":
            parts.append(metric)
            continue

        # Get the value to bind, e.g. experiment_id=42
        value = parameters_by_name[field_name]
        parts.append("%s")
        parameters.append(value)

    return "".join(parts), parameters
