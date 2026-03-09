#!/bin/bash
# ============================================
# Database Initialization Script
# Runs automatically on container start
# ============================================

set -e

echo "============================================"
echo "Initializing Bot SaaS Database"
echo "============================================"

# Wait for PostgreSQL to be ready
until pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "PostgreSQL is ready!"

# Check if database already initialized
SCHEMA_CHECK=$(psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -tAc "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'masters')")

if [ "$SCHEMA_CHECK" = "t" ]; then
  echo "Database already initialized. Skipping..."
else
  echo "Applying database schema..."
  psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /docker-entrypoint-initdb.d/01-schema.sql
  echo "Database schema applied successfully!"
fi

# Run custom scripts if any
if [ -d /docker-entrypoint-initdb.d/scripts ]; then
  echo "Running custom initialization scripts..."
  for script in /docker-entrypoint-initdb.d/scripts/*.sql; do
    if [ -f "$script" ]; then
      echo "Running $(basename "$script")..."
      psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f "$script"
    fi
  done
fi

echo "============================================"
echo "Database initialization complete!"
echo "============================================"
