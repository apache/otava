#!/bin/bash

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

# This is a script that contributors can use to verify release candidates before voting
# Note: ASF rules specifically require each contributor, ultimately committer, to personally,
# that is, manually, inspect a release candidate source tar file before voting on it.
# Scripting this "manual" process is allowed. Also sharing such scripts between contributors
# is allowed. If you use this script, consider adding your own checks or variations to diversify
# the positive impact on quality that this process is intended to have.
# Note that trying to fully automate these checks, for example by putting this script in CI,
# is not allowed. Releases must always be approved via voting, and voters must have personally
# validated the release.


set -e
set -x


PYTHON_VERSION=3.8
PROJECT_NAME="apache-otava"
SHORT_NAME="otava"
PROJECT_VERSION="0.7.0-incubating-rc3"
DIST="dev/incubator"
#DIST="release/incubator"

ASF_BASE_URL="https://dist.apache.org/repos/dist"
KEYS_URL="${ASF_BASE_URL}/release/incubator/KEYS"
BASE_URL="${ASF_BASE_URL}/${DIST}/${SHORT_NAME}/${PROJECT_VERSION}"

TAR_BASE="${PROJECT_NAME}-${PROJECT_VERSION}"
TAR_FILE="${TAR_BASE}-src.tar.gz"
TAR_URL="${BASE_URL}/${TAR_FILE}"


# Just execute the tests, skip the download and unpack
workdir=$1


if [[ ! -d ${workdir} ]]
then
###################################### Download and unpack #########################################3
    uname=asf-verifier-$RANDOM
    uvenv=venv-$uname
    workdir=/tmp/$uname

    set +x

    echo " "

    echo "Please execute:"
    echo ""
    echo "   gpg --fetch-keys $KEYS_URL"
    echo ""
    echo "... manually."
    echo "(For security reasons I won't.)"
    echo ""
    set -x


    mkdir /tmp/$uname
    cd /tmp/$uname

    curl -f "$TAR_URL" > "$TAR_FILE"
    curl -f -o "$TAR_FILE".asc "$TAR_URL".asc
    curl -f -o "$TAR_FILE".sha512 "$TAR_URL".sha512

    gpg -v --verify "$TAR_FILE".asc "$TAR_FILE"
    sha512sum --check "$TAR_FILE".sha512

    tar xvf "$TAR_FILE"
    #cd "$PROJECT_NAME"
    ls -laiFhR
else
    cd $workdir
fi
cd ${SHORT_NAME}-${PROJECT_VERSION}
cat README.md
cat LICENSE
cat DISCLAIMER
cat NOTICE

echo
echo Try to actually execute something
echo

set -x
uv venv --allow-existing
uv pip install .
uv run otava

# Commented out lines from here on are because they don't work
# uv run otava -h
uv run otava analyze -h

uv run otava list-groups  # There are no groups yet
uv run otava --config-file examples/csv/config/otava.yaml analyze -h
uv run otava --config-file examples/csv/config/otava.yaml list-groups
uv run otava --config-file examples/csv/config/otava.yaml list-tests

# This works, but it didn't analyze local.sample
# uv run otava --config-file examples/csv/config/otava.yaml analyze local.sample

# This one fails and prints an "ERROR: ..." message, but doesn't return with nonzero exit
uv run otava --config-file examples/csv/config/otava.yaml analyze --tests-local.sample-file=examples/csv/data/local_sample.csv local.sample


docker compose -f examples/csv/docker-compose.yaml run --build otava analyze local.sample
