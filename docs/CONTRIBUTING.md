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

* Ensure that `python3` points to a version of python >= 3.8 (`python3 --version` will tell you).  If it does not, use [pyenv](https://github.com/pyenv/pyenv) to both install a recent python version and make it your current python.

* There are two wrappers (`poetryw` and `toxw`) that install and run the correct versions of [poetry](https://python-poetry.org) and [tox](https://tox.wiki) for you.

* Run poetry to install dependencies:

```
./poetryw install
```

* Run the development version of otava using poetry:

```
./poetryw run otava ...
```

See the [poetry docs](https://python-poetry.org/docs) for more.

# Running tests

```
./poetryw run pytest
```

...or using [tox](https://tox.readthedocs.io/):

```
./toxw
```

# Linting and formatting

Code-style is enforced using [ruff](https://docs.astral.sh/ruff/) and [flake8](https://flake8.pycqa.org/); import optimisation is handled by [isort](https://pycqa.github.io/isort/) and [autoflake](https://pypi.org/project/autoflake/).  Linting is automatically applied when tox runs tests; if linting fails, you can fix trivial problems with:

```
./toxw -e format
```

# Changing the LICENSE header

To change the license header:
1. Add the `--remove-header` arg to `.pre-commit-config.yaml`
2. Run formatting (this will remove the license header entirely)
```
./toxw -e format
```
3. Remove the `--remove-header` arg from `.pre-commit-config.yaml`
4. Update `ci-tools/license-templates/LICENSE.txt`
5. Run formatting
```
./toxw -e format
```

# Build a docker image

```
./toxw -e docker-build
```
