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

# BigQuery

## Schema

See [schema.sql](../examples/bigquery/schema.sql) for the example schema.

## Usage

Define BigQuery connection details via environment variables:

```bash
export BIGQUERY_PROJECT_ID=...
export BIGQUERY_DATASET=...
export BIGQUERY_VAULT_SECRET=...
```
or in `otava.yaml`.

Also configure the credentials. See [config_credentials.sh](../examples/bigquery/config_credentials.sh) for an example.

The following command shows results for a single test `aggregate_mem` and updates the database with newly found change points:

```bash
$ BRANCH=trunk OTAVA_CONFIG=otava.yaml otava analyze aggregate_mem --update-bigquery
```
