#!/bin/bash
# LangDive Database Restore
# Usage: ./scripts/restore_db.sh [backup_file]
# If no file specified, restores the latest backup

BACKUP_DIR="/Users/yangxuan/PycharmProjects/A01-LangDive/langdive/backend/data/backups"

if [ -n "$1" ]; then
    BACKUP_FILE="$1"
else
    BACKUP_FILE=$(ls -t "$BACKUP_DIR"/langdive_*.sql 2>/dev/null | head -1)
fi

if [ -z "$BACKUP_FILE" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "❌ No backup file found"
    echo "Usage: $0 [backup_file]"
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/langdive_*.sql 2>/dev/null
    exit 1
fi

SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Restoring from: $BACKUP_FILE ($SIZE)"
echo "⚠️  This will REPLACE all current data. Continue? (y/N)"
read -r confirm
if [ "$confirm" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

/opt/homebrew/opt/postgresql@16/bin/psql -U langdive -d langdive -h localhost < "$BACKUP_FILE" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Restore complete"
else
    echo "❌ Restore failed"
fi
