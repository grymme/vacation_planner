#!/bin/bash
#
# Vacation Planner Restore Script
# Restores encrypted PostgreSQL backups
#

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/pi/backups/vacation-planner}"

usage() {
    echo "Usage: $0 <backup_file>"
    echo "Example: $0 vacation_planner_20250115_020000.sql.gz.enc"
    exit 1
}

[ $# -lt 1 ] && usage

BACKUP_FILE="$1"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

if [ ! -f "$BACKUP_PATH" ]; then
    echo "ERROR: Backup file not found: ${BACKUP_PATH}"
    exit 1
fi

echo "Stopping services..."
cd "$(dirname "$0")/.."
docker-compose down

echo "Restoring database from ${BACKUP_FILE}..."

export PGPASSWORD="${POSTGRES_PASSWORD:-vacation_password}"

openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
    -pass pass:"${BACKUP_ENCRYPTION_KEY:-change-this-password}" \
    -in "$BACKUP_PATH" \
    | gunzip \
    | psql \
        -h localhost \
        -U "${POSTGRES_USER:-vacation}" \
        -d "${POSTGRES_DB:-vacation_planner}"

echo "Starting services..."
docker-compose up -d

echo "Restore completed successfully"
