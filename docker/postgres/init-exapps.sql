-- Initialize databases for ExApps
-- This script runs on PostgreSQL startup

-- Create databases for each ExApp (PostgreSQL syntax)
SELECT 'CREATE DATABASE keycloak' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'keycloak')\gexec

-- Grant privileges to nextcloud user
GRANT ALL PRIVILEGES ON DATABASE keycloak TO nextcloud;
