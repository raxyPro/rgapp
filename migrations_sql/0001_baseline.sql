-- 0001_baseline.sql
-- This migration creates the schema migration tracker table.
-- (Your application tables are defined in database.txt / initial DB setup.)

CREATE TABLE IF NOT EXISTS rb_schema_migrations (
  filename VARCHAR(255) NOT NULL PRIMARY KEY,
  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
