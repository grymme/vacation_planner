# Backup Procedures

## Backup Components

### Database (PostgreSQL)

The database contains all critical application data:

| Data Type | Description |
|-----------|-------------|
| Users | User accounts, credentials (hashed), profile data |
| Companies | Company configurations and settings |
| Teams | Team structures and memberships |
| Vacation Requests | All vacation request data |
| Audit Logs | System activity records |
| Invite Tokens | Pending invitation tokens |

### Application Data

| Data Type | Location |
|-----------|----------|
| Configuration | Environment variables (`.env`) |
| Caddy TLS Certificates | `/var/lib/caddy/data` |
| Uploaded Files | N/A (none currently) |

### What is NOT Backed Up

- Log files (should be forwarded to logging system)
- Temporary files
- Container volumes (except database)

## Backup Script

Create the backup script at `scripts/backup.sh`:

```bash
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

# Create encrypted backup
log "Backing up database to ${BACKUP_FILE}..."

# Get database credentials from environment
export PGPASSWORD="${POSTGRES_PASSWORD:-vacation_password}"

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
```

### Make Script Executable

```bash
chmod +x scripts/backup.sh
```

## Restore Procedures

### Full Restore from Backup

```bash
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
```

### Partial Restore (Single Table)

```bash
# Extract specific table from backup
export PGPASSWORD="${POSTGRES_PASSWORD:-vacation_password}"
BACKUP_FILE="vacation_planner_20250115_020000.sql.gz.enc"

openssl enc -aes-256-cbc -d -pbkdf2 -iter 100000 \
    -pass pass:"${BACKUP_ENCRYPTION_KEY}" \
    -in "${BACKUP_DIR}/${BACKUP_FILE}" \
    | gunzip \
    | psql \
        -h localhost \
        -U "${POSTGRES_USER:-vacation}" \
        -d "${POSTGRES_DB:-vacation_planner}" \
        -c "TRUNCATE TABLE users RESTART IDENTITY CASCADE;"
```

## Cron Schedule

### Daily Backup

Add to crontab (`crontab -e`):

```cron
# Daily backup at 2:00 AM
0 2 * * * /home/pi/vacation-planner/scripts/backup.sh >> /var/log/backup.log 2>&1

# Weekly backup retention check (Sundays at 3 AM)
0 3 * * 0 /home/pi/vacation-planner/scripts/verify_backups.sh >> /var/log/backup_verify.log 2>&1
```

### Monthly Long-Term Backup

```cron
# First day of each month at 3 AM - copy to external storage
0 3 1 * * rsync -avz /home/pi/backups/vacation-planner/ /mnt/external-backup/monthly/
```

## Retention Policy

| Data Type | Retention | Reason |
|-----------|-----------|--------|
| Daily backups | 30 days | Quick recovery from recent issues |
| Weekly backups | 12 weeks | Point-in-time recovery |
| Monthly backups | 12 months | Long-term archival |
| Audit logs | 2 years | Compliance requirements |

## Backup Verification

Create verification script at `scripts/verify_backups.sh`:

```bash
#!/bin/bash
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
BACKUP_AGE=$(( $(date +%s) - $(stat -c %Y "$LATEST_BACKUP") ))
if [ $BACKUP_AGE -gt 172800 ]; then
    log "WARNING: Latest backup is older than 2 days"
fi

log "Backup verification completed"
```

## Offsite Backup Recommendations

### Option 1: rsync to External Drive

```bash
# Mount external drive at /mnt/backup
# Add to cron:
0 4 * * * rsync -avz --delete /home/pi/backups/vacation-planner/ /mnt/backup/vacation-planner/
```

### Option 2: Cloud Storage (rclone)

```bash
# Configure rclone for your cloud provider
# Add to cron:
0 5 * * * rclone copy /home/pi/backups/vacation-planner/ remote:vacation-planner-backup/
```

### Option 3: Git LFS (for small deployments)

```bash
# Initialize git repo in backup directory
git lfs track "*.sql.gz.enc"
0 6 * * * cd /home/pi/backups/vacation-planner && git add . && git commit -m "Backup $(date +%Y%m%d)" && git push
```

## Disaster Recovery Checklist

1. **Assess Damage**
   - [ ] Identify affected components
   - [ ] Determine recovery time objective (RTO)
   - [ ] Determine recovery point objective (RPO)

2. **Prepare Recovery Environment**
   - [ ] Ensure hardware is operational
   - [ ] Verify backup files are accessible
   - [ ] Test decryption password

3. **Execute Recovery**
   - [ ] Stop all services
   - [ ] Backup current database (if partially functional)
   - [ ] Restore from latest verified backup
   - [ ] Verify data integrity
   - [ ] Start services

4. **Post-Recovery Validation**
   - [ ] Verify user accounts
   - [ ] Check vacation requests
   - [ ] Test authentication
   - [ ] Verify admin access
   - [ ] Check audit logs

5. **Resume Operations**
   - [ ] Monitor system health
   - [ ] Notify users of any data loss
   - [ ] Document incident
