-- Postgres initialization script.
-- Runs only the first time the postgres container starts with an empty data volume.
-- Creates the dedicated database used by Evolution API (separate from the portal DB).

CREATE DATABASE evolution;
GRANT ALL PRIVILEGES ON DATABASE evolution TO portal;
