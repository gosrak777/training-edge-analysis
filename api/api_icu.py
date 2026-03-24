"""API endpoints for Intervals.icu integration.

This module provides API endpoints that use Intervals.icu as the data source.
Can be imported into the main app or used standalone.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from engine import config, sync_intervals, oura_report, database

# Create router
router = APIRouter(prefix="/api/v1/icu", tags=["Intervals.icu"])


# ═══════════════════════════════════════════════════════════════════════════════
# Health & Config
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/health")
def health_check() -> Dict[str, Any]:
    """Check Intervals.icu API connectivity."""
    configured = config.check_intervals_config()
    return {
        "status": "ok" if configured else "not_configured",
        "intervals_configured": configured,
        "athlete_id": config.INTERVALS_ATHLETE_ID if configured else None,
    }


@router.get("/config")
def get_config() -> Dict[str, Any]:
    """Get current configuration (safe - no API keys)."""
    return {
        "intervals_configured": config.check_intervals_config(),
        "athlete_id": config.INTERVALS_ATHLETE_ID,
        "base_url": config.INTERVALS_BASE_URL,
        "reports_dir": str(config.REPORTS_DIR),
        "db_path": str(config.DB_PATH),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Sync Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sync/activities")
def sync_activities(
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """Sync activities from Intervals.icu."""
    if not config.check_intervals_config():
        raise HTTPException(503, "Intervals.icu not configured")
    
    result = sync_intervals.sync_activities(days=days, limit=limit)
    
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Sync failed"))
    
    return result


@router.post("/sync/wellness")
def sync_wellness(
    days: int = Query(default=14, ge=1, le=90),
) -> Dict[str, Any]:
    """Sync wellness data from Intervals.icu (includes Oura Ring)."""
    if not config.check_intervals_config():
        raise HTTPException(503, "Intervals.icu not configured")
    
    result = sync_intervals.sync_wellness(days=days)
    
    if not result.get("success"):
        raise HTTPException(500, result.get("error", "Sync failed"))
    
    return result


@router.post("/sync/all")
def sync_all(
    days_activities: int = Query(default=7, ge=1, le=90),
    days_wellness: int = Query(default=14, ge=1, le=90),
) -> Dict[str, Any]:
    """Full sync: activities + wellness + fitness history."""
    if not config.check_intervals_config():
        raise HTTPException(503, "Intervals.icu not configured")
    
    return sync_intervals.sync_all(
        days_activities=days_activities,
        days_wellness=days_wellness,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Oura Health Report Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/oura/morning-report")
def get_oura_morning_report() -> Dict[str, Any]:
    """Get Oura morning health summary.
    
    Returns structured health data from Oura Ring (synced via Intervals.icu).
    """
    summary = oura_report.generate_morning_health_summary()
    return summary


@router.get("/oura/morning-report/text")
def get_oura_morning_report_text() -> str:
    """Get Oura morning health summary as formatted text."""
    return oura_report.get_morning_health_report()


@router.get("/oura/trend")
def get_oura_trend(
    days: int = Query(default=7, ge=1, le=30),
) -> List[Dict[str, Any]]:
    """Get Oura wellness trend for the last N days."""
    return oura_report.get_wellness_trend(days=days)


# ═══════════════════════════════════════════════════════════════════════════════
# Data Query Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/activities")
def list_activities(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
) -> List[Dict[str, Any]]:
    """List activities from local database (synced from Intervals)."""
    with database.get_db() as conn:
        return database.list_activities(conn, days=days, limit=limit)


@router.get("/activities/{activity_id}")
def get_activity(activity_id: str) -> Dict[str, Any]:
    """Get single activity details."""
    with database.get_db() as conn:
        # Try as integer first (Intervals IDs can be numeric)
        try:
            act = database.get_activity(conn, int(activity_id))
        except ValueError:
            act = None
        
        if not act:
            raise HTTPException(404, f"Activity {activity_id} not found")
        
        return act


@router.get("/wellness")
def list_wellness(
    days: int = Query(default=30, ge=1, le=365),
) -> List[Dict[str, Any]]:
    """List wellness records from local database."""
    with database.get_db() as conn:
        return database.list_wellness(conn, days=days)


@router.get("/fitness-history")
def get_fitness_history(
    days: int = Query(default=90, ge=1, le=365),
) -> List[Dict[str, Any]]:
    """Get fitness history (CTL/ATL/TSB)."""
    with database.get_db() as conn:
        return database.list_fitness_history(conn, days=days)


# ═══════════════════════════════════════════════════════════════════════════════
# Legacy Compatibility Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/sync")
def sync_legacy(
    days: int = Query(default=7, ge=1, le=90),
) -> Dict[str, Any]:
    """Legacy sync endpoint — redirects to full sync."""
    return sync_intervals.sync_all(days_activities=days, days_wellness=max(days, 14))
