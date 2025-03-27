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

GRAPHITE_SERVER="graphite"
GRAPHITE_PORT=2003

commits=("a1b2c3" "d4e5f6" "g7h8i9" "j1k2l3" "m4n5o6" "p7q8r9")
num_commits=${#commits[@]}

throughput_path="performance-tests.daily.my-product.client.throughput"
throughput_values=(56950 57980 57123 60960 60160 61160)

p50_path="performance-tests.daily.my-product.client.p50"
p50_values=(85 87 88 89 85 87)

cpu_path="performance-tests.daily.my-product.server.cpu"
cpu_values=(0.7 0.9 0.8 0.1 0.3 0.2)


# Function to send throughput to Graphite
send_to_graphite() {
    local throughput_path=$1
    local value=$2
    local timestamp=$3
    local commit=$4
    # send the metric
    echo "${throughput_path} ${value} ${timestamp}" | nc ${GRAPHITE_SERVER} ${GRAPHITE_PORT}
    # annotate the metric
    # Commented out, waiting for https://github.com/apache/otava/issues/24 to be fixed
    #    curl -X POST "http://${GRAPHITE_SERVER}/events/" \
    #        -d "{
    #          \"what\": \"Performance Test\",
    #          \"tags\": [\"perf-test\", \"daily\", \"my-product\"],
    #          \"when\": ${timestamp},
    #          \"data\": {\"commit\": \"${commit}\", \"branch\": \"new-feature\",  \"version\": \"0.0.1\"}
    #        }"
}



sleep 5 # Wait for Graphite to start

start_timestamp=$(date +%s)
timestamp=$start_timestamp

# Send metrics for each commit
for ((i=0; i<${num_commits}; i++)); do
    send_to_graphite ${throughput_path} ${throughput_values[$i]} ${timestamp} ${commits[$i]}
    send_to_graphite ${p50_path} ${p50_values[$i]} ${timestamp} ${commits[$i]}
    send_to_graphite ${cpu_path} ${cpu_values[$i]} ${timestamp} ${commits[$i]}
    timestamp=$((timestamp - 60))
done

## Send each throughput value
#timestamp=$start_timestamp
#for value in "${throughput_values[@]}"; do
#    send_to_graphite ${throughput_path} ${value} ${timestamp}
#    timestamp=$((timestamp - 60))
#done
#
## Send each p50 value
#timestamp=$start_timestamp
#for value in "${p50_values[@]}"; do
#    send_to_graphite ${p50_path} ${value} ${timestamp}
#    timestamp=$((timestamp - 60))
#done
#
## Send each CPU value
#timestamp=$start_timestamp
#for value in "${cpu_values[@]}"; do
#    send_to_graphite ${cpu_path} ${value} ${timestamp}
#    timestamp=$((timestamp - 60))
#done