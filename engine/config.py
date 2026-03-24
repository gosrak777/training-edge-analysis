"""Configuration management — env vars for Intervals.icu + NAS paths."""

from __future__ import annotations

import os
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════════
# Intervals.icu API Configuration
# ═══════════════════════════════════════════════════════════════════════════════

INTERVALS_API_KEY = os.environ.get("INTERVALS_API_KEY", "").strip()
INTERVALS_ATHLETE_ID = os.environ.get("INTERVALS_ATHLETE_ID", "0").strip()
INTERVALS_BASE_URL = os.environ.get("INTERVALS_API_BASE", "https://intervals.icu/api/v1")


def check_intervals_config() -> bool:
    """Check if Intervals.icu API is configured."""
    return bool(INTERVALS_API_KEY)


def get_intervals_auth():
    """Return HTTPBasicAuth tuple for requests."""
    from requests.auth import HTTPBasicAuth
    if not INTERVALS_API_KEY:
        raise RuntimeError("INTERVALS_API_KEY not set")
    return HTTPBasicAuth("API_KEY", INTERVALS_API_KEY)


# ═══════════════════════════════════════════════════════════════════════════════
# NAS / Path Configuration
# ═══════════════════════════════════════════════════════════════════════════════

# Base directory — use env var or default to project root
BASE_DIR = Path(os.environ.get("TRAININGEDGE_BASE_DIR", 
                               str(Path(__file__).resolve().parents[1])))

# Reports output directory (for NAS mounting)
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", str(BASE_DIR / "reports")))

# State directory (database, cache)
STATE_DIR = Path(os.environ.get("TRAININGEDGE_STATE_DIR", str(BASE_DIR / "state")))

# Ensure directories exist
def ensure_dirs():
    """Create necessary directories."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# Database Path
# ═══════════════════════════════════════════════════════════════════════════════

DB_PATH = Path(os.environ.get("TRAININGEDGE_DB_PATH", str(STATE_DIR / "training_edge.db")))


# ═══════════════════════════════════════════════════════════════════════════════
# Oura Integration Settings
# ═══════════════════════════════════════════════════════════════════════════════

# Oura data comes through Intervals.icu wellness sync
# These are the field names in Intervals wellness response
OURA_READINESS_FIELD = "readiness"  # readinessScore from Oura
OURA_HRV_FIELD = "hrv"              # hrv_rmssd from Oura  
OURA_TEMP_FIELD = "bodyTemp"        # body_temp_deviation from Oura


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Garmin Config (deprecated, kept for reference)
# ═══════════════════════════════════════════════════════════════════════════════

# GARMINTOKENS = os.environ.get("GARMINTOKENS", "")
# FIT_DIR = Path(os.environ.get("TRAININGEDGE_FIT_DIR", str(STATE_DIR / "fit_files")))
