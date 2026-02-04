#!/bin/bash
#
# Vacation Planner Backup Verification Script
# Verifies integrity of backup files
#

BACKUP_DIR="${BACKUP_DIR:-/home/pi/backups/vacation-planner}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Verifying backup integrity..."

# Check backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
    log "ERROR: Backup directory not found"
    exit 1
fi

# Get latest backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/vacation_planner_*.sql.gz.enc 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    log "ERROR: No backups found"
    exit 1
fi

log "Testing latest backup: ${LATEST_BACKUP}"

# Test decryption and decompression
if openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
    -pass pass:"${BACKUP_ENCRYPTION_KEY:-change-this-password}" \
    -in "$LATEST_BACKUP" 2>/dev/null | gunzip > /dev/null; then
    log "Backup verification PASSED"
else
    log "ERROR: Backup verification FAILED - file may be corrupted"
    exit 1
fi

# Check backup age
BACKUP_AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST_BACKUP" 2>/dev/null || stat -f %m "$LATEST_BACKUP" 2>/dev/null) ))
if [ $BACKUP_AGE -gt 172800 ]; then
    log "WARNING: Latest backup is older than 2 days"
fi

log "Backup verification completed"
