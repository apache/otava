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
from io import StringIO

import pytest

from otava.config import NestedYAMLConfigFileParser, load_config_from_file
from otava.test_config import CsvTestConfig, GraphiteTestConfig, HistoStatTestConfig


def test_load_graphite_tests():
    config = load_config_from_file("tests/resources/sample_config.yaml")
    tests = config.tests
    assert len(tests) == 4
    test = tests["remote1"]
    assert isinstance(test, GraphiteTestConfig)
    assert len(test.metrics) == 7
    print(test.metrics)
    assert test.prefix == "performance_regressions.my_product.%{BRANCH}.test1"
    assert test.metrics["throughput"].name == "throughput"
    assert test.metrics["throughput"].suffix is not None
    assert test.metrics["p50"].name == "p50"
    assert test.metrics["p50"].direction == -1
    assert test.metrics["p50"].scale == 1.0e-6
    assert test.metrics["p50"].suffix is not None


def test_load_csv_tests():
    config = load_config_from_file("tests/resources/sample_config.yaml")
    tests = config.tests
    assert len(tests) == 4
    test = tests["local1"]
    assert isinstance(test, CsvTestConfig)
    assert len(test.metrics) == 2
    assert len(test.attributes) == 1
    assert test.file == "tests/resources/sample.csv"

    test = tests["local2"]
    assert isinstance(test, CsvTestConfig)
    assert len(test.metrics) == 2
    assert test.metrics["m1"].column == "metric1"
    assert test.metrics["m1"].direction == 1
    assert test.metrics["m2"].column == "metric2"
    assert test.metrics["m2"].direction == -1
    assert len(test.attributes) == 1
    assert test.file == "tests/resources/sample.csv"


def test_load_test_groups():
    config = load_config_from_file("tests/resources/sample_config.yaml")
    groups = config.test_groups
    assert len(groups) == 2
    assert len(groups["remote"]) == 2


def test_load_histostat_config():
    config = load_config_from_file("tests/resources/histostat_test_config.yaml")
    tests = config.tests
    assert len(tests) == 1
    test = tests["histostat-sample"]
    assert isinstance(test, HistoStatTestConfig)
    # 14 tags * 12 tag_metrics == 168 unique metrics
    assert len(test.fully_qualified_metric_names()) == 168


@pytest.mark.parametrize(
    "config_property",
    [
        # property, accessor, env_var, cli_flag, [config value, env value, cli value]
        ("slack_token", lambda c: c.slack.bot_token, "SLACK_BOT_TOKEN", "--slack-token"),
        ("bigquery_project_id", lambda c: c.bigquery.project_id, "BIGQUERY_PROJECT_ID", "--bigquery-project-id"),
        ("bigquery_dataset", lambda c: c.bigquery.dataset, "BIGQUERY_DATASET", "--bigquery-dataset"),
        ("bigquery_credentials", lambda c: c.bigquery.credentials, "BIGQUERY_VAULT_SECRET", "--bigquery-credentials"),
        ("grafana_url", lambda c: c.grafana.url, "GRAFANA_ADDRESS", "--grafana-url"),
        ("grafana_user", lambda c: c.grafana.user, "GRAFANA_USER", "--grafana-user"),
        ("grafana_password", lambda c: c.grafana.password, "GRAFANA_PASSWORD", "--grafana-password"),
        ("graphite_url", lambda c: c.graphite.url, "GRAPHITE_ADDRESS", "--graphite-url"),
        ("postgres_hostname", lambda c: c.postgres.hostname, "POSTGRES_HOSTNAME", "--postgres-hostname"),
        ("postgres_port", lambda c: c.postgres.port, "POSTGRES_PORT", "--postgres-port", 1111, 2222, 3333),
        ("postgres_username", lambda c: c.postgres.username, "POSTGRES_USERNAME", "--postgres-username"),
        ("postgres_password", lambda c: c.postgres.password, "POSTGRES_PASSWORD", "--postgres-password"),
        ("postgres_database", lambda c: c.postgres.database, "POSTGRES_DATABASE", "--postgres-database"),
    ],
    ids=lambda v: v[0],  # use the property name for the parameterized test name
)
def test_configuration_substitutions(config_property):
    config_file = "tests/resources/substitution_test_config.yaml"
    accessor = config_property[1]

    if len(config_property) == 4:
        config_value = f"config_{config_property[0]}"
        env_config_value = f"env_{config_property[0]}"
        cli_config_value = f"cli_{config_property[0]}"
    else:
        config_value = config_property[4]
        env_config_value = config_property[5]
        cli_config_value = config_property[6]

    # test value from config file
    config = load_config_from_file(config_file)
    assert accessor(config) == config_value

    # test env var overrides values from config file
    os.environ[config_property[2]] = str(env_config_value)
    try:
        config = load_config_from_file(config_file)
        assert accessor(config) == env_config_value
    finally:
        os.environ.pop(config_property[2])

    # test cli values override values from config file
    config = load_config_from_file(config_file, arg_overrides=[config_property[3], str(cli_config_value)])
    assert accessor(config) == cli_config_value

    # test cli values override values from config file and env var
    os.environ[config_property[2]] = str(env_config_value)
    try:
        config = load_config_from_file(config_file, arg_overrides=[config_property[3], str(cli_config_value)])
        assert accessor(config) == cli_config_value
    finally:
        os.environ.pop(config_property[2])


def test_config_section_yaml_parser_flattens_only_config_sections():
    """Test that NestedYAMLConfigFileParser only flattens the specified config sections."""

    parser = NestedYAMLConfigFileParser()
    test_yaml = """
graphite:
  url: http://example.com
  timeout: 30
slack:
  bot_token: test-token
  channel: "#alerts"
postgres:
  hostname: localhost
  port: 5432
templates:
    aggregate_mem:
      type: postgres
      time_column: commit_ts
      attributes: [experiment_id, config_id, commit]
      metrics:
        process_cumulative_rate_mean:
          direction: 1
          scale: 1
        process_cumulative_rate_stderr:
          direction: -1
          scale: 1
        process_cumulative_rate_diff:
          direction: -1
          scale: 1
      query: |
        SELECT e.commit,
               e.commit_ts,
               r.process_cumulative_rate_mean,
               r.process_cumulative_rate_stderr,
               r.process_cumulative_rate_diff,
               r.experiment_id,
               r.config_id
        FROM results r
        INNER JOIN configs c ON r.config_id = c.id
        INNER JOIN experiments e ON r.experiment_id = e.id
        WHERE e.exclude_from_analysis = false AND
              e.branch = 'trunk' AND
              e.username = 'ci' AND
              c.store = 'MEM' AND
              c.cache = true AND
              c.benchmark = 'aggregate' AND
              c.instance_type = 'ec2i3.large'
        ORDER BY e.commit_ts ASC;
"""

    stream = StringIO(test_yaml)
    result = parser.parse(stream)

    # Should flatten config sections
    expected_keys = {
        'graphite-url', 'graphite-timeout',
        'slack-bot-token', 'slack-channel',
        'postgres-hostname', 'postgres-port'
    }

    assert set(result.keys()) == expected_keys
    assert result['graphite-url'] == 'http://example.com'
    assert result['graphite-timeout'] == '30'
    assert result['slack-bot-token'] == 'test-token'
    assert result['slack-channel'] == '#alerts'
    assert result['postgres-hostname'] == 'localhost'
    assert result['postgres-port'] == '5432'

    # Should NOT contain any keys from ignored sections
    ignored_sections = {'templates', 'tests', 'test_groups'}
    for key in result.keys():
        section = key.split('-')[0]
        assert section not in ignored_sections, f"Found key '{key}' from ignored section '{section}'"
