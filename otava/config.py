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
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import configargparse
from ruamel.yaml import YAML

from otava.bigquery import BigQueryConfig
from otava.grafana import GrafanaConfig
from otava.graphite import GraphiteConfig
from otava.postgres import PostgresConfig
from otava.slack import SlackConfig
from otava.test_config import TestConfig, create_test_config
from otava.util import merge_dict_list


@dataclass
class Config:
    graphite: Optional[GraphiteConfig]
    grafana: Optional[GrafanaConfig]
    tests: Dict[str, TestConfig]
    test_groups: Dict[str, List[TestConfig]]
    slack: SlackConfig
    postgres: PostgresConfig
    bigquery: BigQueryConfig


@dataclass
class ConfigError(Exception):
    message: str


def load_templates(config: Dict) -> Dict[str, Dict]:
    templates = config.get("templates", {})
    if not isinstance(templates, Dict):
        raise ConfigError("Property `templates` is not a dictionary")
    return templates


def load_tests(config: Dict, templates: Dict) -> Dict[str, TestConfig]:
    tests = config.get("tests", {})
    if not isinstance(tests, Dict):
        raise ConfigError("Property `tests` is not a dictionary")

    result = {}
    for (test_name, test_config) in tests.items():
        template_names = test_config.get("inherit", [])
        if not isinstance(template_names, List):
            template_names = [templates]
        try:
            template_list = [templates[name] for name in template_names]
        except KeyError as e:
            raise ConfigError(f"Template {e.args[0]} referenced in test {test_name} not found")
        test_config = merge_dict_list(template_list + [test_config])
        result[test_name] = create_test_config(test_name, test_config)

    return result


def load_test_groups(config: Dict, tests: Dict[str, TestConfig]) -> Dict[str, List[TestConfig]]:
    groups = config.get("test_groups", {})
    if not isinstance(groups, Dict):
        raise ConfigError("Property `test_groups` is not a dictionary")

    result = {}
    for (group_name, test_names) in groups.items():
        test_list = []
        if not isinstance(test_names, List):
            raise ConfigError(f"Test group {group_name} must be a list")
        for test_name in test_names:
            test_config = tests.get(test_name)
            if test_config is None:
                raise ConfigError(f"Test {test_name} referenced by group {group_name} not found.")
            test_list.append(test_config)

        result[group_name] = test_list

    return result


def load_config_from_parser_args(args: configargparse.Namespace) -> Config:
    config_file = getattr(args, "config_file", None)
    if config_file is not None:
        yaml = YAML(typ="safe")
        config = yaml.load(Path(config_file).read_text())

        templates = load_templates(config)
        tests = load_tests(config, templates)
        groups = load_test_groups(config, tests)
    else:
        logging.warning("Otava configuration file not found or not specified")
        tests = {}
        groups = {}

    return Config(
        graphite=GraphiteConfig.from_parser_args(args),
        grafana=GrafanaConfig.from_parser_args(args),
        slack=SlackConfig.from_parser_args(args),
        postgres=PostgresConfig.from_parser_args(args),
        bigquery=BigQueryConfig.from_parser_args(args),
        tests=tests,
        test_groups=groups,
    )


class NestedYAMLConfigFileParser(configargparse.ConfigFileParser):
    """
    Custom YAML config file parser that supports nested YAML structures.
    Maps nested keys like 'slack: {token: value}' to 'slack-token=value', i.e. CLI argument style.
    Recasts values from YAML inferred types to strings as expected for CLI arguments.
    """

    def parse(self, stream):
        yaml = YAML(typ="safe")
        config_data = yaml.load(stream)
        if config_data is None:
            return {}
        flattened_dict = {}
        self._flatten_dict(config_data, flattened_dict)
        return flattened_dict

    def _flatten_dict(self, nested_dict, flattened_dict, prefix=''):
        """Recursively flatten nested dictionaries using CLI dash-separated notation for keys."""
        if not isinstance(nested_dict, dict):
            return

        for key, value in nested_dict.items():
            new_key = f"{prefix}{key}" if prefix else key

            # yaml keys typically use snake case
            # replace underscore with dash to convert snake case to CLI dash-separated style
            new_key = new_key.replace("_", "-")

            if isinstance(value, dict):
                # Recursively process nested dictionaries
                self._flatten_dict(value, flattened_dict, f"{new_key}-")
            else:
                # Add leaf values to the flattened dictionary
                # Value must be cast to string here, so arg parser can cast from string to expected type later
                flattened_dict[new_key] = str(value)


def create_config_parser() -> configargparse.ArgumentParser:
    parser = configargparse.ArgumentParser(
        add_help=False,
        config_file_parser_class=NestedYAMLConfigFileParser,
        default_config_files=[
            Path().home() / ".otava/conf.yaml",
            Path().home() / ".otava/otava.yaml",
        ],
        allow_abbrev=False,  # required for correct parsing of nested values from config file
    )
    parser.add_argument('--config-file', is_config_file=True, help='Otava config file path', env_var="OTAVA_CONFIG")
    GraphiteConfig.add_parser_args(parser.add_argument_group('Graphite Options', 'Options for Graphite configuration'))
    GrafanaConfig.add_parser_args(parser.add_argument_group('Grafana Options', 'Options for Grafana configuration'))
    SlackConfig.add_parser_args(parser.add_argument_group('Slack Options', 'Options for Slack configuration'))
    PostgresConfig.add_parser_args(parser.add_argument_group('Postgres Options', 'Options for Postgres configuration'))
    BigQueryConfig.add_parser_args(parser.add_argument_group('BigQuery Options', 'Options for BigQuery configuration'))
    return parser


def load_config_from_file(config_file: str, arg_overrides: Optional[List[str]] = None) -> Config:
    if arg_overrides is None:
        arg_overrides = []
    arg_overrides.extend(["--config-file", config_file])
    args, _ = create_config_parser().parse_known_args(args=arg_overrides)
    return load_config_from_parser_args(args)
