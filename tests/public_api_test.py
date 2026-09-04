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

import doctest
import importlib
import re
import subprocess
import sys
import textwrap
from importlib import metadata, resources
from pathlib import Path
from types import ModuleType

import otava

DOCS_API = Path(__file__).parents[1] / "docs/API.md"

# Where each re-exported name is defined. The package root must hand out the
# very same objects, otherwise isinstance() checks would depend on the import
# path a caller happened to use.
DEFINING_MODULES = {
    "AnalysisOptions": "otava.series",
    "AnalyzedSeries": "otava.series",
    "ChangePoint": "otava.change_point_divisive.base",
    "ChangePointGroup": "otava.change_point_divisive.base",
    "ChangePointsByMetric": "otava.change_point_divisive.base",
    "ChangePointsByTime": "otava.change_point_divisive.base",
    "Metric": "otava.series",
    "Series": "otava.series",
    "compute_change_points": "otava.analysis",
}


def test_public_names_are_the_objects_from_their_defining_modules():
    assert set(otava.__all__) == set(DEFINING_MODULES)

    for name, module_name in DEFINING_MODULES.items():
        module = __import__(module_name, fromlist=[name])

        assert getattr(otava, name) is getattr(module, name)


def test_package_root_exports_nothing_beyond_dunder_all():
    exported = {
        name
        for name in vars(otava)
        if not name.startswith("_") and not isinstance(getattr(otava, name), ModuleType)
    }

    assert exported == set(otava.__all__)
    assert otava.__all__ == sorted(otava.__all__)


def test_version_matches_the_installed_distribution():
    assert otava.__version__ == metadata.version("apache-otava")


def test_py_typed_marker_is_part_of_the_package():
    assert resources.files("otava").joinpath("py.typed").is_file()


def test_package_docstring_example_is_accurate():
    results = doctest.testmod(otava, verbose=False)

    assert results.attempted > 0
    assert results.failed == 0


def test_documented_examples_run_and_report_a_change(capsys):
    snippets = re.findall(r"^```python\n(.*?)^```", DOCS_API.read_text(), re.MULTILINE | re.DOTALL)

    assert snippets, f"no python examples found in {DOCS_API}"

    for snippet in snippets:
        exec(compile(snippet, str(DOCS_API), "exec"), {})

    # An example that finds nothing would still run, and would still be wrong.
    assert capsys.readouterr().out.strip()


def test_importing_the_package_does_not_load_optional_service_clients():
    # The extras introduced in #55 only hold if no code path a core-only
    # installation reaches imports a service client. Importing the package root
    # became such a path when it stopped being an empty namespace package.
    script = textwrap.dedent(
        """
        import builtins

        blocked = {"google", "influxdb_client_3", "pg8000", "requests", "slack_sdk"}
        original_import = builtins.__import__

        def import_without_optional_clients(name, globals=None, locals=None, fromlist=(), level=0):
            top_level = name.partition(".")[0]
            if top_level in blocked:
                raise ModuleNotFoundError(f"No module named '{top_level}'", name=top_level)
            return original_import(name, globals, locals, fromlist, level)

        builtins.__import__ = import_without_optional_clients

        import otava

        for name in otava.__all__:
            getattr(otava, name)
        """
    )

    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr


def test_version_falls_back_when_the_distribution_is_not_installed(monkeypatch):
    def not_installed(_):
        raise metadata.PackageNotFoundError("apache-otava")

    monkeypatch.setattr(metadata, "version", not_installed)
    reloaded = importlib.reload(otava)

    try:
        assert reloaded.__version__ == "0.0.0.dev0"
    finally:
        monkeypatch.undo()
        importlib.reload(otava)

    assert otava.__version__ == metadata.version("apache-otava")
