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

import os
import subprocess
import sys

# Python 3.13+ changed argparse formatting for usage lines and option aliases
IS_PYTHON_313_PLUS = sys.version_info >= (3, 13)


def run_help_command(subcommand: str = None) -> subprocess.CompletedProcess:
    """
    Invoke the installed otava CLI (expects entrypoint script) to capture --help output.
    """
    if subcommand is None:
        cmd = ["uv", "run", "otava", "--help"]
    else:
        cmd = ["uv", "run", "otava", subcommand, "--help"]
    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=dict(os.environ, COLUMNS="100"),
    )


def test_otava_help_output():
    result = run_help_command()
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )

    # Python 3.13+ formats the usage line differently (keeps subcommands on one line)
    if IS_PYTHON_313_PLUS:
        usage_line = """\
usage: otava [-h] [--config-file CONFIG_FILE] [--graphite-url GRAPHITE_URL]
             [--grafana-url GRAFANA_URL] [--grafana-user GRAFANA_USER]
             [--grafana-password GRAFANA_PASSWORD] [--slack-token SLACK_TOKEN]
             [--postgres-hostname POSTGRES_HOSTNAME] [--postgres-port POSTGRES_PORT]
             [--postgres-username POSTGRES_USERNAME] [--postgres-password POSTGRES_PASSWORD]
             [--postgres-database POSTGRES_DATABASE] [--bigquery-project-id BIGQUERY_PROJECT_ID]
             [--bigquery-dataset BIGQUERY_DATASET] [--bigquery-credentials BIGQUERY_CREDENTIALS]
             {list-tests,list-metrics,list-groups,analyze,remove-annotations,validate} ..."""
    else:
        usage_line = """\
usage: otava [-h] [--config-file CONFIG_FILE] [--graphite-url GRAPHITE_URL]
             [--grafana-url GRAFANA_URL] [--grafana-user GRAFANA_USER]
             [--grafana-password GRAFANA_PASSWORD] [--slack-token SLACK_TOKEN]
             [--postgres-hostname POSTGRES_HOSTNAME] [--postgres-port POSTGRES_PORT]
             [--postgres-username POSTGRES_USERNAME] [--postgres-password POSTGRES_PASSWORD]
             [--postgres-database POSTGRES_DATABASE] [--bigquery-project-id BIGQUERY_PROJECT_ID]
             [--bigquery-dataset BIGQUERY_DATASET] [--bigquery-credentials BIGQUERY_CREDENTIALS]
             {list-tests,list-metrics,list-groups,analyze,remove-annotations,validate}
             ..."""

    assert (
        result.stdout
        == usage_line + """

Change Detection for Continuous Performance Engineering

positional arguments:
  {list-tests,list-metrics,list-groups,analyze,remove-annotations,validate}
    list-tests          list available tests
    list-metrics        list available metrics for a test
    list-groups         list available groups of tests
    analyze             analyze performance test results
    validate            validates the tests and metrics defined in the configuration

options:
  -h, --help            show this help message and exit
  --config-file CONFIG_FILE
                        Otava config file path [env var: OTAVA_CONFIG]

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

Args that start with '--' can also be set in a config file (specified via --config-file).  In
general, command-line values override environment variables which override config file values
which override defaults.
"""
    )


def test_otava_analyze_help_output():
    result = run_help_command("analyze")
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )

    # Python 3.13+ formats usage lines and option aliases differently
    if IS_PYTHON_313_PLUS:
        usage_and_options = """\
usage: otava analyze [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                     [--grafana-user GRAFANA_USER] [--grafana-password GRAFANA_PASSWORD]
                     [--slack-token SLACK_TOKEN] [--postgres-hostname POSTGRES_HOSTNAME]
                     [--postgres-port POSTGRES_PORT] [--postgres-username POSTGRES_USERNAME]
                     [--postgres-password POSTGRES_PASSWORD]
                     [--postgres-database POSTGRES_DATABASE]
                     [--bigquery-project-id BIGQUERY_PROJECT_ID]
                     [--bigquery-dataset BIGQUERY_DATASET]
                     [--bigquery-credentials BIGQUERY_CREDENTIALS] [--update-grafana]
                     [--update-postgres] [--update-bigquery]
                     [--notify-slack NOTIFY_SLACK [NOTIFY_SLACK ...]] [--cph-report-since DATE]
                     [--output {log,json,regressions_only}] [--branch [STRING]] [--metrics LIST]
                     [--attrs LIST] [--since-commit STRING | --since-version STRING |
                     --since DATE] [--until-commit STRING | --until-version STRING | --until DATE]
                     [--last COUNT] [-P, --p-value PVALUE] [-M MAGNITUDE] [--window WINDOW]
                     [--orig-edivisive ORIG_EDIVISIVE]
                     tests [tests ...]

positional arguments:
  tests                 name of the test or group of the tests

options:
  -h, --help            show this help message and exit
  --update-grafana      Update Grafana dashboards with appropriate annotations of change points
  --update-postgres     Update PostgreSQL database results with change points
  --update-bigquery     Update BigQuery database results with change points
  --notify-slack NOTIFY_SLACK [NOTIFY_SLACK ...]
                        Send notification containing a summary of change points to given Slack
                        channels
  --cph-report-since DATE
                        Sets a limit on the date range of the Change Point History reported to
                        Slack. Same syntax as --since.
  --output {log,json,regressions_only}
                        Output format for the generated report.
  --branch [STRING]     name of the branch
  --metrics LIST        a comma-separated list of metrics to analyze
  --attrs LIST          a comma-separated list of attribute names associated with the runs (e.g.
                        commit, branch, version); if not specified, it will be automatically
                        filled based on available information
  --since-commit STRING
                        the commit at the start of the time span to analyze
  --since-version STRING
                        the version at the start of the time span to analyze
  --since DATE          the start of the time span to analyze; accepts ISO, and human-readable
                        dates like '10 weeks ago'
  --until-commit STRING
                        the commit at the end of the time span to analyze
  --until-version STRING
                        the version at the end of the time span to analyze
  --until DATE          the end of the time span to analyze; same syntax as --since
  --last COUNT          the number of data points to take from the end of the series
  -P, --p-value PVALUE  maximum accepted P-value of a change-point; P denotes the probability that
                        the change-point has been found by a random coincidence, rather than a
                        real difference between the data distributions
  -M, --magnitude MAGNITUDE"""
    else:
        usage_and_options = """\
usage: otava analyze [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                     [--grafana-user GRAFANA_USER] [--grafana-password GRAFANA_PASSWORD]
                     [--slack-token SLACK_TOKEN] [--postgres-hostname POSTGRES_HOSTNAME]
                     [--postgres-port POSTGRES_PORT] [--postgres-username POSTGRES_USERNAME]
                     [--postgres-password POSTGRES_PASSWORD]
                     [--postgres-database POSTGRES_DATABASE]
                     [--bigquery-project-id BIGQUERY_PROJECT_ID]
                     [--bigquery-dataset BIGQUERY_DATASET]
                     [--bigquery-credentials BIGQUERY_CREDENTIALS] [--update-grafana]
                     [--update-postgres] [--update-bigquery]
                     [--notify-slack NOTIFY_SLACK [NOTIFY_SLACK ...]] [--cph-report-since DATE]
                     [--output {log,json,regressions_only}] [--branch [STRING]] [--metrics LIST]
                     [--attrs LIST]
                     [--since-commit STRING | --since-version STRING | --since DATE]
                     [--until-commit STRING | --until-version STRING | --until DATE]
                     [--last COUNT] [-P, --p-value PVALUE] [-M MAGNITUDE] [--window WINDOW]
                     [--orig-edivisive ORIG_EDIVISIVE]
                     tests [tests ...]

positional arguments:
  tests                 name of the test or group of the tests

options:
  -h, --help            show this help message and exit
  --update-grafana      Update Grafana dashboards with appropriate annotations of change points
  --update-postgres     Update PostgreSQL database results with change points
  --update-bigquery     Update BigQuery database results with change points
  --notify-slack NOTIFY_SLACK [NOTIFY_SLACK ...]
                        Send notification containing a summary of change points to given Slack
                        channels
  --cph-report-since DATE
                        Sets a limit on the date range of the Change Point History reported to
                        Slack. Same syntax as --since.
  --output {log,json,regressions_only}
                        Output format for the generated report.
  --branch [STRING]     name of the branch
  --metrics LIST        a comma-separated list of metrics to analyze
  --attrs LIST          a comma-separated list of attribute names associated with the runs (e.g.
                        commit, branch, version); if not specified, it will be automatically
                        filled based on available information
  --since-commit STRING
                        the commit at the start of the time span to analyze
  --since-version STRING
                        the version at the start of the time span to analyze
  --since DATE          the start of the time span to analyze; accepts ISO, and human-readable
                        dates like '10 weeks ago'
  --until-commit STRING
                        the commit at the end of the time span to analyze
  --until-version STRING
                        the version at the end of the time span to analyze
  --until DATE          the end of the time span to analyze; same syntax as --since
  --last COUNT          the number of data points to take from the end of the series
  -P, --p-value PVALUE  maximum accepted P-value of a change-point; P denotes the probability that
                        the change-point has been found by a random coincidence, rather than a
                        real difference between the data distributions
  -M MAGNITUDE, --magnitude MAGNITUDE"""

    assert (
        result.stdout
        == usage_and_options + """
                        minimum accepted magnitude of a change-point computed as abs(new_mean /
                        old_mean - 1.0); use it to filter out stupidly small changes like < 0.01
  --window WINDOW       the number of data points analyzed at once; the window size affects the
                        discriminative power of the change point detection algorithm; large
                        windows are less susceptible to noise; however, a very large window may
                        cause dismissing short regressions as noise so it is best to keep it short
                        enough to include not more than a few change points (optimally at most 1)
  --orig-edivisive ORIG_EDIVISIVE
                        use the original edivisive algorithm with no windowing and weak change
                        points analysis improvements

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

 In general, command-line values override environment variables which override defaults.
"""
    )


def test_otava_list_tests_help_output():
    result = run_help_command("list-tests")
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )
    assert (
        result.stdout
        == """\
usage: otava list-tests [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                        [--grafana-user GRAFANA_USER] [--grafana-password GRAFANA_PASSWORD]
                        [--slack-token SLACK_TOKEN] [--postgres-hostname POSTGRES_HOSTNAME]
                        [--postgres-port POSTGRES_PORT] [--postgres-username POSTGRES_USERNAME]
                        [--postgres-password POSTGRES_PASSWORD]
                        [--postgres-database POSTGRES_DATABASE]
                        [--bigquery-project-id BIGQUERY_PROJECT_ID]
                        [--bigquery-dataset BIGQUERY_DATASET]
                        [--bigquery-credentials BIGQUERY_CREDENTIALS]
                        [group ...]

positional arguments:
  group                 name of the group of the tests

options:
  -h, --help            show this help message and exit

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

 In general, command-line values override environment variables which override defaults.
"""
    )


def test_otava_list_metrics_help_output():
    result = run_help_command("list-metrics")
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )
    assert (
        result.stdout
        == """\
usage: otava list-metrics [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                          [--grafana-user GRAFANA_USER] [--grafana-password GRAFANA_PASSWORD]
                          [--slack-token SLACK_TOKEN] [--postgres-hostname POSTGRES_HOSTNAME]
                          [--postgres-port POSTGRES_PORT] [--postgres-username POSTGRES_USERNAME]
                          [--postgres-password POSTGRES_PASSWORD]
                          [--postgres-database POSTGRES_DATABASE]
                          [--bigquery-project-id BIGQUERY_PROJECT_ID]
                          [--bigquery-dataset BIGQUERY_DATASET]
                          [--bigquery-credentials BIGQUERY_CREDENTIALS]
                          test

positional arguments:
  test                  name of the test

options:
  -h, --help            show this help message and exit

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

 In general, command-line values override environment variables which override defaults.
"""
    )


# Test for list-groups subcommand
def test_otava_list_groups_help_output():
    result = run_help_command("list-groups")
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )
    assert (
        result.stdout
        == """\
usage: otava list-groups [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                         [--grafana-user GRAFANA_USER] [--grafana-password GRAFANA_PASSWORD]
                         [--slack-token SLACK_TOKEN] [--postgres-hostname POSTGRES_HOSTNAME]
                         [--postgres-port POSTGRES_PORT] [--postgres-username POSTGRES_USERNAME]
                         [--postgres-password POSTGRES_PASSWORD]
                         [--postgres-database POSTGRES_DATABASE]
                         [--bigquery-project-id BIGQUERY_PROJECT_ID]
                         [--bigquery-dataset BIGQUERY_DATASET]
                         [--bigquery-credentials BIGQUERY_CREDENTIALS]

options:
  -h, --help            show this help message and exit

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

 In general, command-line values override environment variables which override defaults.
"""
    )


def test_otava_remove_annotations_help_output():
    result = run_help_command("remove-annotations")
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )
    assert (
        result.stdout
        == """\
usage: otava remove-annotations [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                                [--grafana-user GRAFANA_USER]
                                [--grafana-password GRAFANA_PASSWORD] [--slack-token SLACK_TOKEN]
                                [--postgres-hostname POSTGRES_HOSTNAME]
                                [--postgres-port POSTGRES_PORT]
                                [--postgres-username POSTGRES_USERNAME]
                                [--postgres-password POSTGRES_PASSWORD]
                                [--postgres-database POSTGRES_DATABASE]
                                [--bigquery-project-id BIGQUERY_PROJECT_ID]
                                [--bigquery-dataset BIGQUERY_DATASET]
                                [--bigquery-credentials BIGQUERY_CREDENTIALS] [--force]
                                [tests ...]

positional arguments:
  tests                 name of the test or test group

options:
  -h, --help            show this help message and exit
  --force               don't ask questions, just do it

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

 In general, command-line values override environment variables which override defaults.
"""
    )


def test_otava_validate_help_output():
    result = run_help_command("validate")
    assert result.returncode == 0, (
        f"Expected exit code 0, got {result.returncode}. stderr:\n{result.stderr}"
    )
    assert (
        result.stdout
        == """\
usage: otava validate [-h] [--graphite-url GRAPHITE_URL] [--grafana-url GRAFANA_URL]
                      [--grafana-user GRAFANA_USER] [--grafana-password GRAFANA_PASSWORD]
                      [--slack-token SLACK_TOKEN] [--postgres-hostname POSTGRES_HOSTNAME]
                      [--postgres-port POSTGRES_PORT] [--postgres-username POSTGRES_USERNAME]
                      [--postgres-password POSTGRES_PASSWORD]
                      [--postgres-database POSTGRES_DATABASE]
                      [--bigquery-project-id BIGQUERY_PROJECT_ID]
                      [--bigquery-dataset BIGQUERY_DATASET]
                      [--bigquery-credentials BIGQUERY_CREDENTIALS]

options:
  -h, --help            show this help message and exit

Graphite Options:
  Options for Graphite configuration

  --graphite-url GRAPHITE_URL
                        Graphite server URL [env var: GRAPHITE_ADDRESS]

Grafana Options:
  Options for Grafana configuration

  --grafana-url GRAFANA_URL
                        Grafana server URL [env var: GRAFANA_ADDRESS]
  --grafana-user GRAFANA_USER
                        Grafana server user [env var: GRAFANA_USER]
  --grafana-password GRAFANA_PASSWORD
                        Grafana server password [env var: GRAFANA_PASSWORD]

Slack Options:
  Options for Slack configuration

  --slack-token SLACK_TOKEN
                        Slack bot token to use for sending notifications [env var:
                        SLACK_BOT_TOKEN]

PostgreSQL Options:
  Options for PostgreSQL configuration

  --postgres-hostname POSTGRES_HOSTNAME
                        PostgreSQL server hostname [env var: POSTGRES_HOSTNAME]
  --postgres-port POSTGRES_PORT
                        PostgreSQL server port [env var: POSTGRES_PORT]
  --postgres-username POSTGRES_USERNAME
                        PostgreSQL username [env var: POSTGRES_USERNAME]
  --postgres-password POSTGRES_PASSWORD
                        PostgreSQL password [env var: POSTGRES_PASSWORD]
  --postgres-database POSTGRES_DATABASE
                        PostgreSQL database name [env var: POSTGRES_DATABASE]

BigQuery Options:
  Options for BigQuery configuration

  --bigquery-project-id BIGQUERY_PROJECT_ID
                        BigQuery project ID [env var: BIGQUERY_PROJECT_ID]
  --bigquery-dataset BIGQUERY_DATASET
                        BigQuery dataset [env var: BIGQUERY_DATASET]
  --bigquery-credentials BIGQUERY_CREDENTIALS
                        BigQuery credentials file [env var: BIGQUERY_VAULT_SECRET]

 In general, command-line values override environment variables which override defaults.
"""
    )
