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

# Importing results from CSV

> [!TIP]
> See [otava.yaml](../examples/csv/otava.yaml) for the full example configuration.

## Tests

```yaml
tests:
  local.sample:
    type: csv
    file: tests/local_sample.csv
    time_column: time
    attributes: [commit]
    metrics: [metric1, metric2]
    csv_options:
      delimiter: ','
      quotechar: "'"
```

## Example

```bash
docker-compose -f examples/csv/docker-compose.yaml run --build otava bin/otava analyze local.sample
```

Expected output:

```bash
time                       commit      metric1    metric2
-------------------------  --------  ---------  ---------
2024-01-01 02:00:00 +0000  aaa0         154023      10.43
2024-01-02 02:00:00 +0000  aaa1         138455      10.23
2024-01-03 02:00:00 +0000  aaa2         143112      10.29
2024-01-04 02:00:00 +0000  aaa3         149190      10.91
2024-01-05 02:00:00 +0000  aaa4         132098      10.34
2024-01-06 02:00:00 +0000  aaa5         151344      10.69
                                                ·········
                                                   -12.9%
                                                ·········
2024-01-07 02:00:00 +0000  aaa6         155145       9.23
2024-01-08 02:00:00 +0000  aaa7         148889       9.11
2024-01-09 02:00:00 +0000  aaa8         149466       9.13
2024-01-10 02:00:00 +0000  aaa9         148209       9.03
```
