Otava – Change Detection for Continuous Performance Engineering
===============================================================

Apache Otava (incubating) performs statistical analysis of performance test results stored
in CSV files, PostgreSQL, BigQuery, or Graphite database. It finds change-points and notifies about
possible performance regressions.

A typical use-case of otava is as follows:

- A set of performance tests is scheduled repeatedly, such as after each commit is pushed.
- The resulting metrics of the test runs are stored in a time series database (Graphite)
   or appended to CSV files.
- Otava is launched by a Jenkins/Cron job (or an operator) to analyze the recorded
  metrics regularly.
- Otava notifies about significant changes in recorded metrics by outputting text reports or
  sending Slack notifications.

Otava is capable of finding even small, but persistent shifts in metric values,
despite noise in data. It adapts automatically to the level of noise in data and
tries to notify only about persistent, statistically significant changes, be it in the system
under test or in the environment.

Unlike in threshold-based performance monitoring systems, there is no need to setup fixed warning
threshold levels manually for each recorded metric. The level of accepted probability of
false-positives, as well as the minimal accepted magnitude of changes are tunable. Otava is
also capable of comparing the level of performance recorded in two different git histories.
This can be used for example to validate a feature branch against the main branch, perhaps
integrated with a pull request.

See the documentation in [docs/README.md](docs/README.md).


## License

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
