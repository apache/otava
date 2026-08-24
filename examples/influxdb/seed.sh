#!/bin/sh

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

set -eu

: "${INFLUXDB3_AUTH_TOKEN:?INFLUXDB3_AUTH_TOKEN must be set}"

INFLUXDB3_HOST_URL="${INFLUXDB3_HOST_URL:-http://influxdb:8181}"
INFLUXDB3_DATABASE_NAME="${INFLUXDB3_DATABASE_NAME:-performance}"
SEED_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

export INFLUXDB3_HOST_URL INFLUXDB3_DATABASE_NAME

attempt=0
until influxdb3 show databases --format csv >/dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge 60 ]; then
        echo "InfluxDB did not become ready at $INFLUXDB3_HOST_URL" >&2
        exit 1
    fi
    sleep 1
done

if ! influxdb3 show databases --format csv | grep -Fqx "$INFLUXDB3_DATABASE_NAME"; then
    influxdb3 create database "$INFLUXDB3_DATABASE_NAME"
fi

influxdb3 write \
    --database "$INFLUXDB3_DATABASE_NAME" \
    --precision ns \
    --file "$SEED_DIR/data.lp"
