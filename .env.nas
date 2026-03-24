# =============================================================================
# TrainingEdge — NAS Docker Deployment Configuration
# =============================================================================
# 
# 1. Copy this file to .env
# 2. Fill in your API keys
# 3. Adjust paths for your NAS
# 4. Run: docker-compose up -d
# =============================================================================


# ═════════════════════════════════════════════════════════════════════════════
# REQUIRED: Intervals.icu API Configuration
# ═════════════════════════════════════════════════════════════════════════════

# Your Intervals.icu API key (from https://intervals.icu/settings)
INTERVALS_API_KEY=your_api_key_here

# Your Intervals.icu Athlete ID (usually "0" for your own account)
INTERVALS_ATHLETE_ID=0

# Base URL (only change if self-hosting Intervals)
INTERVALS_API_BASE=https://intervals.icu/api/v1


# ═════════════════════════════════════════════════════════════════════════════
# NAS Path Configuration
# ═════════════════════════════════════════════════════════════════════════════

# Host path for wellness data (database, cache)
# Synology example: /volume1/docker/trainingedge/state
# QNAP example: /share/Container/trainingedge/state
WELLNESS_DATA_PATH=./state

# Host path for reports output
# Synology example: /volume1/reports/trainingedge
# QNAP example: /share/reports/trainingedge
REPORTS_HOST_PATH=./reports


# ═════════════════════════════════════════════════════════════════════════════
# Web Application Settings
# ═════════════════════════════════════════════════════════════════════════════

# Access password for web dashboard (recommended for NAS)
TRAININGEDGE_PASSWORD=your_secure_password

# Session secret (auto-generated if empty)
# TRAININGEDGE_SESSION_SECRET=$(openssl rand -hex 32)


# ═════════════════════════════════════════════════════════════════════════════
# Sync Settings
# ═════════════════════════════════════════════════════════════════════════════

# Auto-sync interval in hours (0 to disable)
TRAININGEDGE_SYNC_INTERVAL_HOURS=6

# Run mode:
# - web: Web server only
# - cron: Web server + daily cron sync at 7 AM (RECOMMENDED)
# - sync: One-time sync then exit
MODE=cron


# ═════════════════════════════════════════════════════════════════════════════
# Optional: LLM for AI Training Plans
# ═════════════════════════════════════════════════════════════════════════════

# OPENAI_API_KEY=sk-...
# Or other LLM providers...
