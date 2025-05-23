/*
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
*/

CREATE TABLE IF NOT EXISTS configs (
    id BIGINT PRIMARY KEY NOT ENFORCED,
    benchmark STRING NOT NULL,
    scenario STRING NOT NULL,
    store STRING NOT NULL,
    instance_type STRING NOT NULL,
    cache BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
    id BIGINT PRIMARY KEY NOT ENFORCED,
    ts TIMESTAMP NOT NULL,
    branch STRING NOT NULL,
    commit STRING NOT NULL,
    commit_ts TIMESTAMP NOT NULL,
    username STRING NOT NULL,
    details_url STRING NOT NULL,
    exclude_from_analysis BOOLEAN DEFAULT false NOT NULL,
    exclude_reason STRING
);

CREATE TABLE IF NOT EXISTS results (
    experiment_id BIGINT NOT NULL REFERENCES flink_sql.experiments(id) NOT ENFORCED,
    config_id BIGINT NOT NULL REFERENCES flink_sql.configs(id) NOT ENFORCED,

    process_cumulative_rate_mean BIGINT NOT NULL,
    process_cumulative_rate_stderr BIGINT NOT NULL,
    process_cumulative_rate_diff BIGINT NOT NULL,

    process_cumulative_rate_mean_rel_forward_change FLOAT64,
    process_cumulative_rate_mean_rel_backward_change FLOAT64,
    process_cumulative_rate_mean_p_value DECIMAL,

    process_cumulative_rate_stderr_rel_forward_change FLOAT64,
    process_cumulative_rate_stderr_rel_backward_change FLOAT64,
    process_cumulative_rate_stderr_p_value DECIMAL,

    process_cumulative_rate_diff_rel_forward_change FLOAT64,
    process_cumulative_rate_diff_rel_backward_change FLOAT64,
    process_cumulative_rate_diff_p_value DECIMAL,

    PRIMARY KEY (experiment_id, config_id) NOT ENFORCED
);