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

from importlib import import_module
from types import ModuleType


class MissingOptionalDependencyError(ModuleNotFoundError):
    pass


def import_optional_dependency(module_name: str, extra_name: str) -> ModuleType:
    try:
        return import_module(module_name)
    except ModuleNotFoundError as err:
        missing_module = err.name
        if missing_module and (
            module_name == missing_module or module_name.startswith(f"{missing_module}.")
        ):
            raise MissingOptionalDependencyError(
                f"Optional dependency '{module_name}' is required for this operation. "
                f"Install it with: pip install 'apache-otava[{extra_name}]'",
                name=module_name,
            ) from err
        raise
