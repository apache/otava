# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.8.0-slim-buster
# So that STDOUT/STDERR is printed
ENV PYTHONUNBUFFERED="1"

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
    curl \
    virtualenv \
    && rm -rf /var/lib/apt/lists/*

# Get poetry package
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.8.3
# Adding poetry to PATH
ENV PATH="/root/.local/bin/:$PATH"

# Copy the rest of the program over
COPY --chown=otava:otava . ${OTAVA_HOME}

ENV PATH="${OTAVA_HOME}/bin:$PATH"

RUN  --mount=type=ssh \
    virtualenv --python python3.8 venv && \
    . venv/bin/activate && \
    poetry install -v && \
    mkdir -p bin && \
    ln -s ../venv/bin/otava ${OTAVA_HOME}/bin
