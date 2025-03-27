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

# Support functions for bootstrapping python tools

python=${PYTHON:-python3}

# set -x would generate a lot of noise when we activate the venv, so
# we use this hand-crafted equivalent here:
run()
{
    echo "$@" 1>&2
    "$@"
}

build_dir="$thisdir/build"
venvs_dir="$build_dir/venvs"
bin_dir="$build_dir/wrappers/bin"

install_tool()
{
    tool="$1"
    shift

    pip_spec="$1"
    shift

    test -f "$bin_dir/$tool" && return

    run mkdir -p "$venvs_dir" "$bin_dir"

    venv="$venvs_dir/$tool"

    run "$python" -m venv "$venv"

    # Run in a subshell to prevent the activate/deactivate steps
    # interfering with pyenv
    (
        run source "$venv/bin/activate"
        run "$python" -m pip install -qqq --upgrade pip
        run "$python" -m pip install -qqq $pip_spec
        run ln -fs "../../venvs/$tool/bin/$tool" "$bin_dir/$tool"
        run deactivate
    )
}

run_tool()
{
    tool="$1"
    shift

    # Ensure that the tool has access to all the bootstrapped tools
    PATH="$bin_dir:$PATH"

    exec "$bin_dir/$tool" "$@"
}

install_and_run_tool()
{
    tool="$1"
    shift

    pip_spec="$1"
    shift

    install_tool "$tool" "$pip_spec"
    run_tool "$tool" "$@"
}
