# Importing results from PostgreSQL

> [!TIP]
> See [hunter.yaml](../examples/postgresql/hunter.yaml) for the full example configuration.

## PostgreSQL Connection
The following block contains PostgreSQL connection details:

```yaml
postgres:
  hostname: ...
  port: ...
  username: ...
  password: ...
  database: ...
```

These variables can be specified directly in `hunter.yaml` or passed as environment variables:

```yaml
postgres:
  hostname: ${POSTGRES_HOSTNAME}
  port: ${POSTGRES_PORT}
  username: ${POSTGRES_USERNAME}
  password: ${POSTGRES_PASSWORD}
  database: ${POSTGRES_DATABASE}
```

## Tests

Test configuration contains queries selecting experiment data, a time column, and a list of columns to analyze:

```yaml
tests:
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
```

## Example

### Usage

Start docker-compose with PostgreSQL in one tab:

```bash
docker-compose -f examples/postgresql/docker-compose.yaml up --force-recreate --always-recreate-deps --renew-anon-volumes
````

Run Hunter in the other tab to show results for a single test `aggregate_mem` and update the database with newly found change points:

```bash
docker-compose -f examples/postgresql/docker-compose.yaml run --build hunter bin/hunter analyze aggregate_mem --update-postgres
```

Expected output:

```bash                                                                                                                                                                                                       0.0s
time                       experiment_id       commit      process_cumulative_rate_mean    process_cumulative_rate_stderr    process_cumulative_rate_diff
-------------------------  ------------------  --------  ------------------------------  --------------------------------  ------------------------------
2024-03-13 10:03:02 +0000  aggregate-36e5ccd2  36e5ccd2                           61160                              2052                           13558
2024-03-25 10:03:02 +0000  aggregate-d5460f38  d5460f38                           60160                              2142                           13454
2024-04-02 10:03:02 +0000  aggregate-bc9425cb  bc9425cb                           60960                              2052                           13053
                                                         ······························
                                                                                  -5.6%
                                                         ······························
2024-04-06 10:03:02 +0000  aggregate-14df1b11  14df1b11                           57123                              2052                           14052
2024-04-13 10:03:02 +0000  aggregate-ac40c0d8  ac40c0d8                           57980                              2052                           13521
2024-04-27 10:03:02 +0000  aggregate-0af4ccbc  0af4ccbc                           56950                              2052                           13532
```

### Configuration

See [hunter.yaml](../examples/postgresql/hunter.yaml) for the example configuration:
* Block `postgres` contains connection details to the PostgreSQL database.
* Block `templates` contains common pieces of configuration used by all tests - time column and a list of attributes and metrics.
* Block `tests` contains configuration for the individual tests, specifically a query that fetches analyzed columns sorted by commit timestamp.

[schema.sql](../examples/postgresql/init-db/schema.sql) contains the schema used in this example.

[docker-compose.yaml](../examples/postgresql/docker-compose.yaml) contains example config required to connect to PosgreSQL:
1. `POSTGRES_*` environment variables are used to pass connection details to the container.
2. `HUNTER_CONFIG` is the path to the configuration file described above.
3. `BRANCH` variable is used within `HUNTER_CONFIG` to analyze experiment results only for a specific branch.


### CLI arguments

* `--update-postgres` - updates the database with newly found change points.
