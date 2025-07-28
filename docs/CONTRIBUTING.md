<!--
 Licensed to the Apache Software Foundation (ASF) under one
 or more contributor license agreements.  See the NOTICE file
 distributed with this work for additional information
 regarding copyright ownership.  The ASF licenses this file
 to you under the Apache License, Version 2.0 (the
 "License"); you may not use this file except in compliance
 with the License.  You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing,
 software distributed under the License is distributed on an
 "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 KIND, either express or implied.  See the License for the
 specific language governing permissions and limitations
 under the License.
 -->

# Setting up for development

* The project uses [uv](https://docs.astral.sh/uv/) for dependency management and [tox](https://tox.wiki) for testing environments.

* Install dependencies using uv:

```
uv sync --all-extras --dev
```

* Run the development version of otava using uv:

```
uv run otava ...
```

See the [uv docs](https://docs.astral.sh/uv/) for more.

# Running tests

```
uv run pytest
```

...or using [tox](https://tox.readthedocs.io/):

```
uv run tox
```

# Linting and formatting

Code-style is enforced using [ruff](https://docs.astral.sh/ruff/) and [flake8](https://flake8.pycqa.org/); import optimisation is handled by [isort](https://pycqa.github.io/isort/) and [autoflake](https://pypi.org/project/autoflake/).  Linting is automatically applied when tox runs tests; if linting fails, you can fix trivial problems with:

```
uv run tox -e format
```

# Changing the LICENSE header

To change the license header:
1. Add the `--remove-header` arg to `.pre-commit-config.yaml`
2. Run formatting (this will remove the license header entirely)
```
uv run tox -e format
```
3. Remove the `--remove-header` arg from `.pre-commit-config.yaml`
4. Update `ci-tools/license-templates/LICENSE.txt`
5. Run formatting
```
uv run tox -e format
```

# Build a docker image

```
uv run tox -e docker-build
```
