Hunter – Hunts Performance Regressions
======================================

_This is an unsupported open source project created by DataStax employees._


Hunter performs statistical analysis of performance test results stored
in CSV files, PostgreSQL, BigQuery, or Graphite database. It finds change-points and notifies about
possible performance regressions.

A typical use-case of hunter is as follows:

- A set of performance tests is scheduled repeatedly.
- The resulting metrics of the test runs are stored in a time series database (Graphite)
   or appended to CSV files.
- Hunter is launched by a Jenkins/Cron job (or an operator) to analyze the recorded
  metrics regularly.
- Hunter notifies about significant changes in recorded metrics by outputting text reports or
  sending Slack notifications.

Hunter is capable of finding even small, but persistent shifts in metric values,
despite noise in data. It adapts automatically to the level of noise in data and
tries to notify only about persistent, statistically significant changes, be it in the system
under test or in the environment.

Unlike in threshold-based performance monitoring systems, there is no need to setup fixed warning
threshold levels manually for each recorded metric. The level of accepted probability of
false-positives, as well as the minimal accepted magnitude of changes are tunable. Hunter is
also capable of comparingthe level of performance recorded in two different periods of time – which
is useful for e.g. validating the performance of the release candidate vs the previous release of your product.

Backward compatibility may be broken any time.

See the documentation in [docs/README.md](docs/README.md).


## License

Copyright 2021 DataStax Inc

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
