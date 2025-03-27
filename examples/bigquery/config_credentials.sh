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

# Configure the GCP BigQuery key.
touch bigquery_credentials.json
export BIGQUERY_CREDENTIALS=$(readlink -f bigquery_credentials.json)
echo "Loading ${BIGQUERY_CREDENTIALS} to export analysis summaries to BigQuery/Metabase."
# ie: export BIGQUERY_VAULT_SECRET=v1/ci/kv/gcp/flink_sql_bigquery
vault kv get -field=json "${BIGQUERY_VAULT_SECRET}" > "${BIGQUERY_CREDENTIALS}"
# You may also copy your credential json directly to the bigquery_credentials.json for this to work.
chmod 600 "${BIGQUERY_CREDENTIALS}"