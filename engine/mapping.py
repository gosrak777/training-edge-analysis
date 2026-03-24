"""Data mapper — Intervals.icu JSON fields → Garmin-compatible internal format.

This is the critical adapter layer that allows the rest of the codebase
to work with Intervals.icu data without knowing the source changed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# ═══════════════════════════════════════════════════════════════════════════════
# Activity Field Mapping: Intervals → Internal
# ═══════════════════════════════════════════════════════════════════════════════

ACTIVITY_FIELD_MAP = {
    # Intervals field name: internal field name
    "id": "id",
    "name": "name",
    "type": "sport_type",  # will be mapped to sport via _map_sport_type
    "start_date_local": "start_time",
    "distance": "distance_m",
    "moving_time": "total_timer_s",
    "elapsed_time": "total_elapsed_s",
    "average_heartrate": "avg_hr",
    "max_heartrate": "max_hr",
    "average_watts": "avg_power",
    "max_watts": "max_power",
    "average_speed": "avg_speed",
    "max_speed": "max_speed",
    "average_cadence": "avg_cadence",
    "max_cadence": "max_cadence",
    "total_elevation_gain": "total_ascent",
    "calories": "total_calories",
    "average_temp": "avg_temperature",
    
    # Intervals computed metrics (icu_ prefix)
    "icu_weighted_avg_watts": "normalized_power",
    "icu_training_load": "tss",
    "icu_intensity": "intensity_factor",
    "icu_ftp": "device_ftp",
    "icu_eftp": "estimated_ftp",
    "icu_ctl": "ctl",
    "icu_atl": "atl",
    "icu_w_prime": "w_prime",
    
    # External IDs
    "external_id": "external_id",  # Garmin activity ID if synced
}


# ═══════════════════════════════════════════════════════════════════════════════
# Wellness Field Mapping: Intervals → Internal (including Oura data)
# ═══════════════════════════════════════════════════════════════════════════════

WELLNESS_FIELD_MAP = {
    # Date
    "id": "date",  # Intervals uses date as ID
    
    # Fitness/Fatigue (from Intervals calculations)
    "ctl": "ctl",
    "atl": "atl",
    "tsb": "tsb",
    "rampRate": "ramp_rate",
    
    # Sleep data (may come from Oura via Intervals)
    "sleepSecs": "sleep_secs",
    "sleepScore": "sleep_score",
    
    # Oura-specific fields (synced through Intervals)
    "readiness": "readiness",           # Oura readinessScore
    "hrv": "hrv",                       # Oura hrv_rmssd  
    "bodyTemp": "body_temp_deviation",  # Oura body_temp_deviation
    "restingHR": "resting_hr",          # Oura resting_hr or Intervals calc
    
    # Other wellness
    "steps": "steps",
    "weight": "weight_kg",
}


# ═══════════════════════════════════════════════════════════════════════════════
# Sport Type Mapping
# ═══════════════════════════════════════════════════════════════════════════════

SPORT_TYPE_MAP = {
    "ride": "cycling",
    "cycling": "cycling",
    "virtualride": "cycling",
    "run": "running", 
    "running": "running",
    "swim": "swimming",
    "swimming": "swimming",
    "weighttraining": "training",
    "strength_training": "training",
    "workout": "training",
    "yoga": "yoga",
    "rest": "rest",
}


def map_sport_type(intervals_type: Optional[str]) -> str:
    """Map Intervals activity type to internal sport name."""
    if not intervals_type:
        return "unknown"
    return SPORT_TYPE_MAP.get(intervals_type.lower(), intervals_type.lower())


# ═══════════════════════════════════════════════════════════════════════════════
# Data Transformation Functions
# ═══════════════════════════════════════════════════════════════════════════════

def _safe_float(val: Any) -> Optional[float]:
    """Safely convert to float."""
    if val is None:
        return None
    try:
        return round(float(val), 2)
    except (TypeError, ValueError):
        return None


def _safe_int(val: Any) -> Optional[int]:
    """Safely convert to int."""
    if val is None:
        return None
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return None


def transform_activity(intervals_activity: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Intervals.icu activity JSON to internal format.
    
    This is the main adapter function that maps all fields.
    """
    act = intervals_activity
    
    # Build internal format
    result = {
        # Core identity
        "id": act.get("id"),
        "external_id": act.get("external_id"),  # Original Garmin ID if exists
        "name": act.get("name", "Untitled"),
        "sport": map_sport_type(act.get("type")),
        
        # Timing
        "start_time": act.get("start_date_local"),
        "date": act.get("start_date_local", "")[:10] if act.get("start_date_local") else None,
        "total_elapsed_s": _safe_float(act.get("elapsed_time")),
        "total_timer_s": _safe_float(act.get("moving_time")),
        
        # Distance & Speed
        "distance_m": _safe_float(act.get("distance")),
        "avg_speed": _safe_float(act.get("average_speed")),
        "max_speed": _safe_float(act.get("max_speed")),
        
        # Heart Rate
        "avg_hr": _safe_int(act.get("average_heartrate")),
        "max_hr": _safe_int(act.get("max_heartrate")),
        
        # Power (from Intervals computed fields)
        "avg_power": _safe_int(act.get("average_watts")),
        "max_power": _safe_int(act.get("max_watts")),
        "normalized_power": _safe_float(act.get("icu_weighted_avg_watts")),
        "intensity_factor": _safe_float(act.get("icu_intensity")),
        "tss": _safe_float(act.get("icu_training_load")),
        "device_ftp": _safe_float(act.get("icu_ftp")),
        "estimated_ftp": _safe_float(act.get("icu_eftp")),
        "w_prime": _safe_float(act.get("icu_w_prime")),
        
        # Cadence
        "avg_cadence": _safe_int(act.get("average_cadence")),
        "max_cadence": _safe_int(act.get("max_cadence")),
        
        # Elevation & Environment
        "total_ascent": _safe_float(act.get("total_elevation_gain")),
        "total_descent": _safe_float(act.get("total_elevation_loss")),
        "avg_temperature": _safe_float(act.get("average_temp")),
        
        # Energy
        "total_calories": _safe_int(act.get("calories")),
        
        # Training Effect (if available)
        "aerobic_te": _safe_float(act.get("training_stress_score")),  # Approximation
        "anaerobic_te": None,  # Not directly available from Intervals
        
        # Source marker
        "source": "intervals.icu",
        "intervals_id": act.get("id"),
    }
    
    # Remove None values for cleaner storage
    return {k: v for k, v in result.items() if v is not None}


def transform_wellness(intervals_wellness: Dict[str, Any]) -> Dict[str, Any]:
    """Transform Intervals.icu wellness JSON to internal format.
    
    Includes Oura Ring data that syncs through Intervals.
    """
    w = intervals_wellness
    
    # Convert sleep seconds to hours
    sleep_secs = w.get("sleepSecs")
    sleep_hours = round(sleep_secs / 3600, 2) if sleep_secs else None
    
    result = {
        # Date
        "date": w.get("id"),  # Intervals uses date as ID
        
        # Fitness/Fatigue metrics
        "ctl": _safe_float(w.get("ctl")),
        "atl": _safe_float(w.get("atl")),
        "tsb": _safe_float(w.get("tsb")),
        "ramp_rate": _safe_float(w.get("rampRate")),
        
        # Sleep
        "sleep_hours": sleep_hours,
        "sleep_score": _safe_float(w.get("sleepScore")),
        
        # ═══════════════════════════════════════════════════════════════════
        # Oura Ring Data (Critical for illness monitoring)
        # ═══════════════════════════════════════════════════════════════════
        "readiness": _safe_float(w.get("readiness")),           # Oura readinessScore
        "hrv": _safe_float(w.get("hrv")),                       # Oura hrv_rmssd
        "body_temp_deviation": _safe_float(w.get("bodyTemp")),  # Oura body_temp_deviation
        
        # Other metrics
        "resting_hr": _safe_int(w.get("restingHR")),
        "steps": _safe_int(w.get("steps")),
        "weight_kg": _safe_float(w.get("weight")),
        
        # Source marker
        "source": "intervals.icu",
        "has_oura_data": bool(w.get("readiness") or w.get("hrv")),
    }
    
    return {k: v for k, v in result.items() if v is not None}


def transform_activities_list(intervals_activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform a list of Intervals activities."""
    return [transform_activity(act) for act in intervals_activities if act.get("id")]


def transform_wellness_list(intervals_wellness_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Transform a list of Intervals wellness records."""
    return [transform_wellness(w) for w in intervals_wellness_list if w.get("id")]


# ═══════════════════════════════════════════════════════════════════════════════
# Reverse Mapping (for updates back to Intervals format if needed)
# ═══════════════════════════════════════════════════════════════════════════════

def to_intervals_format(internal_activity: Dict[str, Any]) -> Dict[str, Any]:
    """Convert internal format back to Intervals-like format for API calls."""
    # This is used if we need to push data back to Intervals
    reverse_map = {v: k for k, v in ACTIVITY_FIELD_MAP.items()}
    
    result = {}
    for internal_key, value in internal_activity.items():
        intervals_key = reverse_map.get(internal_key, internal_key)
        result[intervals_key] = value
    
    return result
