#!/bin/bash
set -e

# Initialize databases for ExApps
# This script runs on PostgreSQL startup

echo "Creating ExApp databases..."

# Function to create database if it doesn't exist
create_db_if_not_exists() {
    local db=$1
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
        GRANT ALL PRIVILEGES ON DATABASE $db TO $POSTGRES_USER;
EOSQL
    echo "Database $db ready"
}

# Create databases for each ExApp.
#
# A list, not a loop over one word: adding the next ExApp's database is meant
# to be an edit to EXAPP_DATABASES and nothing else. ShellCheck flagged the
# original `for db in keycloak` (SC2043 — "this loop will only ever run once"),
# which is exactly right about the shape and exactly wrong about the intent.
EXAPP_DATABASES=(keycloak)

for db in "${EXAPP_DATABASES[@]}"; do
    create_db_if_not_exists "$db"
done

echo "ExApp databases initialized successfully!"
