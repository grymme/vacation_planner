#!/bin/bash
#
# Vacation Planner Backup Script
# Creates encrypted PostgreSQL backups with retention management
#

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/pi/backups/vacation-planner}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/vacation_planner_${DATE}.sql.gz.enc"

# Logging
LOG_FILE="${BACKUP_DIR}/backup.log"
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "Starting backup process..."

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Check database connection
if ! pg_isready -h localhost -p 5432 -q 2>/dev/null; then
    log "ERROR: Database is not available"
    exit 1
fi

# Get database credentials from environment
export PGPASSWORD="${POSTGRES_PASSWORD:-vacation_password}"

log "Backing up database to ${BACKUP_FILE}..."

# Create backup with compression and encryption
pg_dump \
    -h localhost \
    -U "${POSTGRES_USER:-vacation}" \
    -d "${POSTGRES_DB:-vacation_planner}" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    | gzip \
    | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 100000 \
        -pass pass:"${BACKUP_ENCRYPTION_KEY:-change-this-password}" \
        -out "$BACKUP_FILE"

# Verify backup file
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup completed successfully: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    log "ERROR: Backup file is empty or missing"
    exit 1
fi

# Cleanup old backups
log "Cleaning up backups older than ${RETENTION_DAYS} days..."
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "vacation_planner_*.sql.gz.enc" -mtime +${RETENTION_DAYS})
if [ -n "$OLD_BACKUPS" ]; then
    echo "$OLD_BACKUPS" | xargs rm -f
    log "Removed $(echo "$OLD_BACKUPS" | wc -l) old backup(s)"
else
    log "No old backups to remove"
fi

# List current backups
log "Current backups:"
ls -lh "$BACKUP_DIR"/vacation_planner_*.sql.gz.enc 2>/dev/null | tail -5

log "Backup process completed"
