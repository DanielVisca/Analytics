-- Migration: add extracted property columns to analytics.events (run once on existing tables)
-- Run after init: clickhouse-client < schemas/ddl/clickhouse_events_migrate_extracted_props.sql

ALTER TABLE analytics.events ADD COLUMN IF NOT EXISTS utm_source LowCardinality(Nullable(String)) DEFAULT NULL;
ALTER TABLE analytics.events ADD COLUMN IF NOT EXISTS utm_medium LowCardinality(Nullable(String)) DEFAULT NULL;
ALTER TABLE analytics.events ADD COLUMN IF NOT EXISTS utm_campaign LowCardinality(Nullable(String)) DEFAULT NULL;
ALTER TABLE analytics.events ADD COLUMN IF NOT EXISTS current_url Nullable(String) DEFAULT NULL;
