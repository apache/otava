FROM python:3.13.2-slim-bookworm
# So that STDOUT/STDERR is printed
ENV PYTHONUNBUFFERED="1"

# We create the default user and group to run unprivileged
ENV HUNTER_HOME /srv/hunter
WORKDIR ${HUNTER_HOME}

RUN groupadd --gid 8192 hunter && \
    useradd --uid 8192 --shell /bin/false --create-home --no-log-init --gid hunter hunter && \
    chown hunter:hunter ${HUNTER_HOME}

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
RUN curl -sSL https://install.python-poetry.org | python3 - --version 2.1.1
# Adding poetry to PATH
ENV PATH="/root/.local/bin/:$PATH"

# # Copy the rest of the program over
COPY --chown=hunter:hunter . ${HUNTER_HOME}

ENV PATH="${HUNTER_HOME}/bin:$PATH"

RUN  --mount=type=ssh \
    virtualenv --python python3.13 venv && \
    . venv/bin/activate && \
    poetry install -v && \
    mkdir -p bin && \
    ln -s ../venv/bin/hunter ${HUNTER_HOME}/bin