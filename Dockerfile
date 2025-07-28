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

FROM python:3.8-slim-bookworm
# So that STDOUT/STDERR is printed
ENV PYTHONUNBUFFERED="1"
ARG UV_VERSION=0.8.3
ENV UV_VERSION=${UV_VERSION}

# We create the default user and group to run unprivileged
ENV OTAVA_HOME /srv/otava
WORKDIR ${OTAVA_HOME}

RUN groupadd --gid 8192 otava && \
    useradd --uid 8192 --shell /bin/false --create-home --no-log-init --gid otava otava && \
    chown otava:otava ${OTAVA_HOME}

# First let's just get things updated.
# Install System dependencies
RUN apt-get update --assume-yes && \
    apt-get install -o 'Dpkg::Options::=--force-confnew' -y --force-yes -q \
    git \
    openssh-client \
    gcc \
    clang \
    build-essential \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy the rest of the program over
COPY --chown=otava:otava . ${OTAVA_HOME}

ENV PATH="${OTAVA_HOME}/bin:$PATH"

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv --mount=type=ssh \
    uv pip install --system -e ".[dev]" && \
    mkdir -p bin && \
    ln -s ../venv/bin/otava ${OTAVA_HOME}/bin
