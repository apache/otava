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

# Importing results from Graphite

> [!TIP]
> See [otava.yaml](../examples/graphite/config/otava.yaml) for the full example configuration.

## Graphite and Grafana Connection

The following block contains Graphite and Grafana connection details:

```yaml
graphite:
  url: ...

grafana:
  url: ...
  user: ...
  password: ...
```

These variables can be specified directly in `otava.yaml` or passed as environment variables:

```yaml
graphite:
  url: ${GRAPHITE_ADDRESS}

grafana:
  url: ${GRAFANA_ADDRESS}
  user: ${GRAFANA_USER}
  password: ${GRAFANA_PASSWORD}
```


## Tests

### Importing results from Graphite

Test configuration contains queries selecting experiment data from Graphite. This is done by specifying the Graphite
path prefix common for all the test's metrics and suffixes for each of the metrics recorded by the test run.

```yaml
tests:
  my-product.test:
    type: graphite
    prefix: performance-tests.daily.my-product
    metrics:
      throughput:
        suffix: client.throughput
      response-time:
        suffix: client.p50
        direction: -1    # lower is better
      cpu-load:
        suffix: server.cpu
        direction: -1    # lower is better
```

### Tags
The optional `tags` property contains the tags that are used to query for Graphite events that store
additional test run metadata such as run identifier, commit, branch and product version information.

The following command will post an event with the test run metadata:
```shell
$ curl -X POST "http://graphite_address/events/" \
    -d '{
      "what": "Performance Test",
      "tags": ["perf-test", "daily", "my-product"],
      "when": 1537884100,
      "data": {"commit": "fe6583ab", "branch": "new-feature", "version": "0.0.1"}
    }'
```

Posting those events is not mandatory, but when they are available, Otava is able to
filter data by commit or version using `--since-commit` or `--since-version` selectors.

#### Supported Metadata Schema
The following keys are supported within the `data` dictionary:

| Field | Description | Default Value |
| :--- | :--- | :--- |
| **`test_owner`** | The user or team responsible for the run. | `"null"` |
| **`test_name`** | The name of the test suite executed. | `"null"` |
| **`run_id`** | Unique identifier for the specific run. | `"null"` |
| **`status`** | The outcome (e.g., `success`, `failure`). | `"null"` |
| **`version`** | The product version being tested. | `"null"` |
| **`branch`** | The VCS branch name. | `"null"` |
| **`commit`** | The specific commit hash. | `"null"` |
| **`start_time`** | Timestamp of test start. | `when` (from Graphite) |
| **`end_time`** | Timestamp of test end. | `when` (from Graphite) |

## Example

Start docker-compose with Graphite in one tab:

```bash
docker-compose -f examples/graphite/docker-compose.yaml up --force-recreate --always-recreate-deps --renew-anon-volumes
````

Run otava in another tab:

```bash
docker-compose -f examples/graphite/docker-compose.yaml run --rm otava analyze my-product.test --since=-10m
```

Expected output:

```bash
time                       run    branch       version    commit      throughput    response_time    cpu_usage
-------------------------  -----  -----------  ---------  --------  ------------  ---------------  -----------
2026-02-22 18:51:10 +0000  null   new-feature  0.0.1      p7q8r9           61160               87          0.2
2026-02-22 18:52:10 +0000  null   new-feature  0.0.1      m4n5o6           60160               85          0.3
2026-02-22 18:53:10 +0000  null   new-feature  0.0.1      j1k2l3           60960               89          0.1
                                                                    ············                   ···········  
                                                                           -5.6%                       +300.0%  
                                                                    ············                   ···········  
2026-02-22 18:54:10 +0000  null   new-feature  0.0.1      g7h8i9           57123               88          0.8
2026-02-22 18:55:10 +0000  null   new-feature  0.0.1      d4e5f6           57980               87          0.9
2026-02-22 18:56:10 +0000  null   new-feature  0.0.1      a1b2c3           56950               85          0.7
```
