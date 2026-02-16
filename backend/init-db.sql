-- Optional init script for PostgreSQL container.
-- Ensures database is ready. Custom extensions can be added here.
-- Encoding/locale are set via POSTGRES_INITDB_ARGS in docker-compose.
-- SELECT 1 ensures script runs successfully (PostgreSQL requires at least one statement).
SELECT 1;
