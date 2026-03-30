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
# JSON Data Source

> **Tip**
> See [examples/](../examples/) for sample configuration files.

## Overview

`JsonImporter` reads benchmark results from a local JSON file and feeds them into Otava for change-point analysis. It is the simplest data source to set up — no external database or service is required.

The importer caches parsed file content in memory, so a file is only read once per session even if multiple tests reference the same path.

---

## Expected JSON Format

The input file must be a JSON array. Each element represents a single benchmark run.
```json
[
  {
    "timestamp": 1711929600,
    "metrics": [
      { "name": "throughput", "value": 4821.0 },
      { "name": "p99_latency_ms", "value": 142.7 }
    ],
    "attributes": {
      "branch": "main",
      "commit": "a3f9c12"
    }
  },
  {
    "timestamp": 1712016000,
    "metrics": [
      { "name": "throughput", "value": 5013.0 },
      { "name": "p99_latency_ms", "value": 138.2 }
    ],
    "attributes": {
      "branch": "main",
      "commit": "b7d2e45"
    }
  }
]
```

---

## Fields

### `timestamp`

- **Type:** integer (Unix epoch seconds)
- **Required:** yes
- Identifies when the benchmark run occurred. Used for time-range filtering via `DataSelector`.

### `metrics`

- **Type:** array of objects
- **Required:** yes
- Each object must have:
  - `name` (string) — unique identifier for the metric within this run
  - `value` (number) — the measured value
- Metric names are collected dynamically across all entries in the file. Names must be consistent across runs for change-point analysis to be meaningful.

### `attributes`

- **Type:** object (string → string)
- **Required:** yes if `branch` filtering is used
- Arbitrary key-value pairs describing the run context (e.g. branch, commit, version).
- The `branch` key is treated specially: if a branch is specified via `DataSelector` or `base_branch` in the config, only runs where `attributes["branch"]` matches that value are included.

---

## Configuration Example

Add a test with `type: json` to your `otava.yaml`:
```yaml
tests:
  my_benchmark:
    type: json
    file: path/to/results.json
    base_branch: main
```

| Field | Required | Description |
|---|---|---|
| `type` | yes | Must be `json` |
| `file` | yes | file: Path to the JSON file |
| `base_branch` | no | If set, only runs from this branch are analyzed by default |

---

## Behavior

- **File loading:** The file is read in full when first accessed. Parsed content is cached in memory for the lifetime of the session — repeated calls with the same file path do not re-read from disk.
- **Metric discovery:** All metric names are collected by scanning every entry in the file. The resulting set is unordered.
- **Attribute discovery:** Attribute keys are collected the same way — by scanning all entries.
- **Branch filtering:** If `selector.branch` is set, only runs where `attributes["branch"]` equals that value are included. If not set but `base_branch` is configured, that value is used instead. If neither is set, all runs are included.
- **Metric filtering:** If `selector.metrics` is set, only metrics whose names appear in that list are included. Others are silently skipped.
- **Time filtering:** Entries outside `selector.since_time` / `selector.until_time` are excluded. An invalid range (since > until) raises an error.
- **Truncation:** After filtering, only the last `selector.last_n_points` entries are kept for time, data, and attributes.

---

## Limitations

- The entire file is read into memory at once. Very large files may cause high memory usage.
- There is no schema validation. Missing or malformed fields will cause a `KeyError` at runtime.
- The `branch` filter requires the key `"branch"` to exist inside `attributes` on every entry — if it is absent on any entry that would otherwise be included, the importer will raise a `KeyError`.
- Attribute values are expected to be strings. No type coercion is performed.
- The file path is resolved at config load time; a missing file raises a `TestConfigError` immediately.

---

## Example Usage

Run analysis on a test backed by a JSON file:
otava analyze my_benchmark
