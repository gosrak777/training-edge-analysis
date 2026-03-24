"""Intervals.icu sync — replacement for Garmin Connect sync.

Fetches activities and wellness data (including Oura Ring metrics) from
Intervals.icu REST API using HTTP Basic Auth.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import requests

from . import config, database, mapping


# ═══════════════════════════════════════════════════════════════════════════════
# API Client
# ═══════════════════════════════════════════════════════════════════════════════

def _make_request(path: str, **params: Any) -> Any:
    """Make authenticated request to Intervals.icu API."""
    url = f"{config.INTERVALS_BASE_URL}{path}"
    auth = config.get_intervals_auth()
    
    resp = requests.get(
        url,
        params={k: v for k, v in params.items() if v is not None},
        auth=auth,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# Data Fetching
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_activities(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """Fetch activities from Intervals.icu.
    
    Endpoint: GET /api/v1/athlete/{id}/activities
    """
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    
    path = f"/athlete/{config.INTERVALS_ATHLETE_ID}/activities"
    
    activities = _make_request(
        path,
        oldest=start_date,
        newest=end_date,
        limit=limit,
    )
    
    return activities if isinstance(activities, list) else []


def fetch_wellness(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch wellness data from Intervals.icu (includes Oura Ring data).
    
    Endpoint: GET /api/v1/athlete/{id}/wellness
    
    Oura fields available:
    - readiness: Oura readinessScore
    - hrv: Oura hrv_rmssd
    - bodyTemp: Oura body_temp_deviation
    """
    if not end_date:
        end_date = date.today().isoformat()
    if not start_date:
        start_date = (date.today() - timedelta(days=14)).isoformat()
    
    path = f"/athlete/{config.INTERVALS_ATHLETE_ID}/wellness"
    
    wellness = _make_request(
        path,
        oldest=start_date,
        newest=end_date,
    )
    
    return wellness if isinstance(wellness, list) else []


def fetch_activity_detail(activity_id: str) -> Optional[Dict[str, Any]]:
    """Fetch detailed activity data.
    
    Endpoint: GET /api/v1/athlete/{id}/activities/{activity_id}
    """
    path = f"/athlete/{config.INTERVALS_ATHLETE_ID}/activities/{activity_id}"
    
    try:
        return _make_request(path)
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return None
        raise


# ═══════════════════════════════════════════════════════════════════════════════
# Data Processing & Storage
# ═══════════════════════════════════════════════════════════════════════════════

def process_and_store_activity(intervals_activity: Dict[str, Any]) -> Dict[str, Any]:
    """Transform and store a single activity."""
    # Transform using mapping adapter
    activity_data = mapping.transform_activity(intervals_activity)
    
    # Store in database
    with database.get_db() as conn:
        database.upsert_activity(conn, activity_data)
    
    return activity_data


def process_and_store_wellness(intervals_wellness: Dict[str, Any]) -> Dict[str, Any]:
    """Transform and store wellness data (including Oura metrics)."""
    # Transform using mapping adapter
    wellness_data = mapping.transform_wellness(intervals_wellness)
    
    # Store in database
    with database.get_db() as conn:
        database.upsert_wellness(conn, wellness_data)
    
    return wellness_data


# ═══════════════════════════════════════════════════════════════════════════════
# Sync Orchestration
# ═══════════════════════════════════════════════════════════════════════════════

def sync_activities(days: int = 7, limit: int = 50) -> Dict[str, Any]:
    """Sync recent activities from Intervals.icu.
    
    Returns:
        Summary dict with count and any errors.
    """
    print(f"🔄 Syncing activities from Intervals.icu (last {days} days)...")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    
    try:
        intervals_acts = fetch_activities(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            limit=limit,
        )
    except Exception as e:
        return {"success": False, "error": str(e), "synced": 0}
    
    synced = 0
    errors = []
    
    for act in intervals_acts:
        act_id = act.get("id", "unknown")
        try:
            process_and_store_activity(act)
            synced += 1
            print(f"  ✓ {act.get('name', 'Untitled')} ({act.get('start_date_local', 'N/A')[:10]}) — TSS: {act.get('icu_training_load', 'N/A')}")
        except Exception as e:
            errors.append(f"{act_id}: {str(e)}")
            print(f"  ✗ Activity {act_id}: {e}")
    
    return {
        "success": True,
        "synced": synced,
        "total_fetched": len(intervals_acts),
        "errors": errors,
    }


def sync_wellness(days: int = 14) -> Dict[str, Any]:
    """Sync wellness data from Intervals.icu (includes Oura Ring data).
    
    Critical Oura fields:
    - readiness: Daily readiness score (0-100)
    - hrv: HRV RMSSD in ms
    - bodyTemp: Body temperature deviation from baseline
    """
    print(f"🔄 Syncing wellness data from Intervals.icu (last {days} days)...")
    print(f"   (Includes Oura Ring: readiness, HRV, body temp)")
    
    end_date = date.today()
    start_date = end_date - timedelta(days=max(days - 1, 0))
    
    try:
        intervals_wellness = fetch_wellness(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
    except Exception as e:
        return {"success": False, "error": str(e), "synced": 0}
    
    synced = 0
    oura_records = 0
    errors = []
    
    for w in intervals_wellness:
        date_str = w.get("id", "unknown")
        try:
            result = process_and_store_wellness(w)
            synced += 1
            
            # Count Oura-enriched records
            if result.get("has_oura_data"):
                oura_records += 1
                readiness = result.get("readiness", "N/A")
                hrv = result.get("hrv", "N/A")
                print(f"  ✓ {date_str} — Oura Ready: {readiness}, HRV: {hrv}")
            else:
                print(f"  ✓ {date_str}")
                
        except Exception as e:
            errors.append(f"{date_str}: {str(e)}")
            print(f"  ✗ Wellness {date_str}: {e}")
    
    return {
        "success": True,
        "synced": synced,
        "oura_enriched": oura_records,
        "total_fetched": len(intervals_wellness),
        "errors": errors,
    }


def update_fitness_history() -> Dict[str, Any]:
    """Update fitness_history table from wellness data.
    
    Uses CTL/ATL from Intervals.icu wellness sync.
    """
    print("🔄 Updating fitness history...")
    
    with database.get_db() as conn:
        # Get wellness records with CTL/ATL
        rows = conn.execute(
            """SELECT date, ctl, atl, tsb, ramp_rate 
               FROM wellness 
               WHERE ctl IS NOT NULL 
               ORDER BY date"""
        ).fetchall()
        
        updated = 0
        for row in rows:
            # Get daily TSS sum from activities
            tss_row = conn.execute(
                "SELECT SUM(tss) as daily_tss FROM activities WHERE date = ?",
                (row["date"],)
            ).fetchone()
            daily_tss = tss_row["daily_tss"] or 0
            
            database.upsert_fitness(conn, {
                "date": row["date"],
                "ctl": row["ctl"],
                "atl": row["atl"],
                "tsb": row["tsb"],
                "ramp_rate": row["ramp_rate"],
                "daily_tss": daily_tss,
            })
            updated += 1
    
    print(f"  ✓ Updated {updated} fitness records")
    return {"success": True, "updated": updated}


def sync_all(days_activities: int = 7, days_wellness: int = 14) -> Dict[str, Any]:
    """Full sync: activities + wellness + fitness history."""
    print("=" * 60)
    print("🚀 Starting full sync from Intervals.icu")
    print("=" * 60)
    
    # Check config
    if not config.check_intervals_config():
        return {
            "success": False,
            "error": "Intervals.icu not configured. Set INTERVALS_API_KEY and INTERVALS_ATHLETE_ID"
        }
    
    # Sync activities
    act_result = sync_activities(days=days_activities)
    
    # Sync wellness (includes Oura data)
    wellness_result = sync_wellness(days=days_wellness)
    
    # Update fitness history
    fitness_result = update_fitness_history()
    
    print("=" * 60)
    print("✅ Sync complete")
    print("=" * 60)
    
    return {
        "success": True,
        "activities": act_result,
        "wellness": wellness_result,
        "fitness": fitness_result,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Backward Compatibility Aliases
# ═══════════════════════════════════════════════════════════════════════════════

# These allow existing code to call sync_recent() without knowing the source changed
def sync_recent(days: int = 7, **kwargs) -> List[Dict[str, Any]]:
    """Backward-compatible wrapper for sync_activities.
    
    Returns list of synced activities (legacy compatibility).
    """
    result = sync_activities(days=days, limit=kwargs.get("limit", 50))
    
    # Also sync wellness
    sync_wellness(days=max(days, 14))
    update_fitness_history()
    
    # Return empty list on error for compatibility
    if not result.get("success"):
        return []
    
    # Fetch and return the synced activities from DB
    with database.get_db() as conn:
        from_date = (date.today() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT * FROM activities WHERE date >= ? ORDER BY date DESC",
            (from_date,)
        ).fetchall()
        return [dict(row) for row in rows]


def sync_garmin_wellness(days: int = 14) -> Dict[str, Any]:
    """Backward-compatible wrapper — now syncs from Intervals (includes Oura)."""
    return sync_wellness(days=days)
