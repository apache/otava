\c benchmark_results;

CREATE TABLE IF NOT EXISTS configs (
    id SERIAL PRIMARY KEY,
    benchmark TEXT NOT NULL,
    store TEXT NOT NULL,
    instance_type TEXT NOT NULL,
    cache BOOLEAN NOT NULL,
    UNIQUE(benchmark,
           store,
           cache,
           instance_type)
);

CREATE TABLE IF NOT EXISTS experiments (
    id TEXT PRIMARY KEY,
    ts TIMESTAMPTZ NOT NULL,
    branch TEXT NOT NULL,
    commit TEXT NOT NULL,
    commit_ts TIMESTAMPTZ NOT NULL,
    username TEXT NOT NULL,
    details_url TEXT NOT NULL,
    exclude_from_analysis BOOLEAN DEFAULT false NOT NULL,
    exclude_reason TEXT
);

CREATE TABLE IF NOT EXISTS results (
  experiment_id TEXT NOT NULL REFERENCES experiments(id),
  config_id INTEGER NOT NULL REFERENCES configs(id),

  process_cumulative_rate_mean BIGINT NOT NULL,
  process_cumulative_rate_stderr BIGINT NOT NULL,
  process_cumulative_rate_diff BIGINT NOT NULL,

  process_cumulative_rate_mean_rel_forward_change DOUBLE PRECISION,
  process_cumulative_rate_mean_rel_backward_change DOUBLE PRECISION,
  process_cumulative_rate_mean_p_value DECIMAL,

  process_cumulative_rate_stderr_rel_forward_change DOUBLE PRECISION,
  process_cumulative_rate_stderr_rel_backward_change DOUBLE PRECISION,
  process_cumulative_rate_stderr_p_value DECIMAL,

  process_cumulative_rate_diff_rel_forward_change DOUBLE PRECISION,
  process_cumulative_rate_diff_rel_backward_change DOUBLE PRECISION,
  process_cumulative_rate_diff_p_value DECIMAL,

  PRIMARY KEY (experiment_id, config_id)
);

-- configurations --
INSERT INTO configs (id, benchmark, store, instance_type, cache) VALUES
    (1, 'aggregate', 'MEM', 'ec2i3.large', true),
    (2, 'aggregate', 'TIME_ROCKS', 'ec2i3.large', true);

-- experiments --
INSERT INTO experiments
    (id, ts, branch, commit, commit_ts, username, details_url)
VALUES
    ('aggregate-36e5ccd2', '2024-03-14 12:03:02+00', 'trunk', '36e5ccd2', '2024-03-13 10:03:02+00', 'ci', 'https://example.com/experiments/aggregate-36e5ccd2'),
    ('aggregate-d5460f38', '2024-03-27 12:03:02+00', 'trunk', 'd5460f38', '2024-03-25 10:03:02+00', 'ci', 'https://example.com/experiments/aggregate-d5460f38'),
    ('aggregate-bc9425cb', '2024-04-01 12:03:02+00', 'trunk', 'bc9425cb', '2024-04-02 10:03:02+00', 'ci', 'https://example.com/experiments/aggregate-bc9425cb'),
    ('aggregate-14df1b11', '2024-04-07 12:03:02+00', 'trunk', '14df1b11', '2024-04-06 10:03:02+00', 'ci', 'https://example.com/experiments/aggregate-14df1b11'),
    ('aggregate-ac40c0d8', '2024-04-14 12:03:02+00', 'trunk', 'ac40c0d8', '2024-04-13 10:03:02+00', 'ci', 'https://example.com/experiments/aggregate-ac40c0d8'),
    ('aggregate-0af4ccbc', '2024-04-28 12:03:02+00', 'trunk', '0af4ccbc', '2024-04-27 10:03:02+00', 'ci', 'https://example.com/experiments/aggregate-0af4ccbc');


INSERT INTO results (experiment_id, config_id, process_cumulative_rate_mean, process_cumulative_rate_stderr, process_cumulative_rate_diff)
VALUES
    ('aggregate-36e5ccd2', 1, 61160, 2052, 13558),
    ('aggregate-36e5ccd2', 2, 59250, 2599, 15557),

    ('aggregate-d5460f38', 1, 60160, 2142, 13454),
    ('aggregate-d5460f38', 2, 58316, 2573, 16028),

    ('aggregate-bc9425cb', 1, 60960, 2052, 13053),
    ('aggregate-bc9425cb', 2, 59021, 2459, 15259),

    ('aggregate-14df1b11', 1, 57123, 2052, 14052),
    ('aggregate-14df1b11', 2, 54725, 2291, 15558),

    ('aggregate-ac40c0d8', 1, 57980, 2052, 13521),
    ('aggregate-ac40c0d8', 2, 54250, 2584, 15558),

    ('aggregate-0af4ccbc', 1, 56950, 2052, 13532),
    ('aggregate-0af4ccbc', 2, 54992, 2311, 15585);
