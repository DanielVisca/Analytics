-- Analytics events table for ClickHouse
-- Run in default database or create analytics DB first: CREATE DATABASE IF NOT EXISTS analytics;

CREATE DATABASE IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.events
(
    timestamp DateTime64(3),
    uuid Nullable(UUID),
    event String,
    distinct_id String,
    project_id String DEFAULT 'default',
    properties String DEFAULT '{}',
    lib LowCardinality(Nullable(String)) DEFAULT NULL,
    lib_version Nullable(String) DEFAULT NULL,
    device_id Nullable(String) DEFAULT NULL
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (project_id, toDate(timestamp), distinct_id, timestamp)
TTL toDateTime(timestamp) + INTERVAL 90 DAY
SETTINGS index_granularity = 8192;

-- Optional: materialized view for daily event counts per project (for fast dashboards)
-- CREATE MATERIALIZED VIEW analytics.events_daily
-- ENGINE = SummingMergeTree()
-- PARTITION BY toYYYYMM(date)
-- ORDER BY (project_id, date, event)
-- AS SELECT
--     toDate(timestamp) AS date,
--     project_id,
--     event,
--     count() AS cnt
-- FROM analytics.events
-- GROUP BY date, project_id, event;
