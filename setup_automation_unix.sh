#!/bin/bash
# MLB Edge v2.4 — One-line cron setup for Linux / Mac
# Run: chmod +x setup_automation_unix.sh && ./setup_automation_unix.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_CMD="cd \"$SCRIPT_DIR\" && python3 run.py >> \"$SCRIPT_DIR/data/cron.log\" 2>&1"
SCORE_CMD="cd \"$SCRIPT_DIR\" && python3 score_yesterday.py >> \"$SCRIPT_DIR/data/cron.log\" 2>&1"

# Detect Python
PYTHON="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON="python"
    else
        echo "Python not found. Install python3 first."
        exit 1
    fi
fi

echo "Setting up cron jobs for MLB Edge..."
echo "  Run daily at 11:00 AM"
echo "  Score daily at 7:00 AM"

# Write to a temporary crontab file
crontab -l 2>/dev/null > /tmp/mlb_edge_crontab || true

# Remove old MLB Edge entries if they exist
sed -i '/# MLB Edge Auto/d' /tmp/mlb_edge_crontab

# Add new entries (11:00 AM and 7:00 AM daily)
# Cron format: min hour day month day_of_week command
cat >> /tmp/mlb_edge_crontab << EOF
0 11 * * * cd "$SCRIPT_DIR" && $PYTHON run.py >> "$SCRIPT_DIR/data/cron.log" 2>&1 # MLB Edge Auto Run
0 7 * * * cd "$SCRIPT_DIR" && $PYTHON score_yesterday.py >> "$SCRIPT_DIR/data/cron.log" 2>&1 # MLB Edge Auto Score
EOF

crontab /tmp/mlb_edge_crontab
rm /tmp/mlb_edge_crontab

echo ""
echo "Done. Cron jobs installed:"
crontab -l | grep "MLB Edge Auto"
echo ""
echo "Logs will append to: $SCRIPT_DIR/data/cron.log"
echo "To remove: run 'crontab -e' and delete the # MLB Edge Auto lines"
