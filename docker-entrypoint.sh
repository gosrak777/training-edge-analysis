#!/bin/bash
set -e

echo "=========================================="
echo "  TrainingEdge — Intervals.icu Edition"
echo "=========================================="

# Check required environment variables
echo "🔍 Checking configuration..."

if [ -z "$INTERVALS_API_KEY" ]; then
    echo "❌ ERROR: INTERVALS_API_KEY is not set!"
    echo "   Please set your Intervals.icu API key in environment variables."
    exit 1
fi

if [ -z "$INTERVALS_ATHLETE_ID" ]; then
    echo "⚠️  WARNING: INTERVALS_ATHLETE_ID not set, using default: 0"
    export INTERVALS_ATHLETE_ID=0
fi

echo "✅ Configuration OK"
echo "   - Athlete ID: $INTERVALS_ATHLETE_ID"
echo "   - Reports Dir: ${REPORTS_DIR:-/app/reports}"
echo "   - State Dir: ${TRAININGEDGE_STATE_DIR:-/app/state}"

# Run database migration if needed
echo ""
echo "🔄 Running database migration..."
python scripts/migrate_db.py || echo "⚠️  Migration warning (may be already up to date)"

# Create directories if not exist
mkdir -p "${REPORTS_DIR:-/app/reports}"
mkdir -p "${TRAININGEDGE_STATE_DIR:-/app/state}"

# Determine run mode
MODE=${MODE:-"web"}

case "$MODE" in
    "sync")
        echo ""
        echo "🚀 Running one-time sync..."
        python -c "
from engine import sync_intervals, config
if config.check_intervals_config():
    result = sync_intervals.sync_all(days_activities=7, days_wellness=14)
    print(f\"Sync complete: {result}\")
else:
    print('Intervals not configured')
"
        ;;
    
    "cron")
        echo ""
        echo "⏰ Starting cron scheduler..."
        echo "   Sync schedule: Daily at 7:00 AM"
        
        # Start cron in background
        cron
        
        # Also start web server for API access
        echo ""
        echo "🌐 Starting web server on port 8000..."
        exec uvicorn api.app:app --host 0.0.0.0 --port 8000 --log-level info
        ;;
    
    "web"|*)
        echo ""
        echo "🌐 Starting web server on port 8000..."
        echo "   API Documentation: http://localhost:8000/docs"
        echo ""
        exec uvicorn api.app:app --host 0.0.0.0 --port 8000 --log-level info
        ;;
esac
