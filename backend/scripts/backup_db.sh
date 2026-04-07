#!/bin/bash
# LangDive Database Backup
# Usage: ./scripts/backup_db.sh
# Backs up PostgreSQL to timestamped SQL file

BACKUP_DIR="/Users/yangxuan/PycharmProjects/A01-LangDive/langdive/backend/data/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/langdive_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

# pg_dump the entire database
/opt/homebrew/opt/postgresql@16/bin/pg_dump -U langdive -d langdive -h localhost --no-password > "$BACKUP_FILE" 2>&1

if [ $? -eq 0 ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ Backup saved: $BACKUP_FILE ($SIZE)"

    # Keep only last 10 backups
    ls -t "$BACKUP_DIR"/langdive_*.sql | tail -n +11 | xargs rm -f 2>/dev/null
    TOTAL=$(ls "$BACKUP_DIR"/langdive_*.sql 2>/dev/null | wc -l | tr -d ' ')
    echo "   Total backups: $TOTAL (keeping last 10)"
else
    echo "❌ Backup failed!"
    cat "$BACKUP_FILE"
    rm -f "$BACKUP_FILE"
fi
