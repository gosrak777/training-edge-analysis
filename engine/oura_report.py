"""Oura Ring health report generator — for illness monitoring and daily readiness.

Generates morning health summary from Oura data synced through Intervals.icu.
This is displayed at the beginning of cycling analysis reports.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from . import database


def get_latest_wellness_with_oura(days_back: int = 3) -> Optional[Dict[str, Any]]:
    """Get the most recent wellness record with Oura data."""
    with database.get_db() as conn:
        from_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        row = conn.execute(
            """SELECT * FROM wellness 
               WHERE date >= ? AND (readiness IS NOT NULL OR hrv IS NOT NULL)
               ORDER BY date DESC LIMIT 1""",
            (from_date,)
        ).fetchone()
        
        return dict(row) if row else None


def get_wellness_trend(days: int = 7) -> List[Dict[str, Any]]:
    """Get wellness trend for the last N days."""
    with database.get_db() as conn:
        from_date = (date.today() - timedelta(days=days)).isoformat()
        
        rows = conn.execute(
            """SELECT date, readiness, hrv, resting_hr, body_temp_deviation, sleep_score
               FROM wellness 
               WHERE date >= ?
               ORDER BY date""",
            (from_date,)
        ).fetchall()
        
        return [dict(row) for row in rows]


def _get_indicator(current: Optional[float], previous: Optional[float], lower_is_better: bool = False) -> str:
    """Get trend indicator emoji."""
    if current is None or previous is None:
        return ""
    
    diff = current - previous
    if abs(diff) < 0.5:  # Negligible change
        return "→"
    
    if lower_is_better:
        return "✅" if diff < 0 else "⚠️"
    else:
        return "✅" if diff > 0 else "⚠️"


def generate_morning_health_summary() -> Dict[str, Any]:
    """Generate comprehensive morning health summary from Oura data.
    
    Returns structured data for report generation.
    """
    latest = get_latest_wellness_with_oura()
    if not latest:
        return {
            "has_data": False,
            "message": "⚠️ 暂无 Oura 数据，请确认 Oura Ring 已同步至 Intervals.icu"
        }
    
    # Get previous day for comparison
    current_date = latest.get("date", date.today().isoformat())
    with database.get_db() as conn:
        prev_row = conn.execute(
            "SELECT * FROM wellness WHERE date < ? ORDER BY date DESC LIMIT 1",
            (current_date,)
        ).fetchone()
        previous = dict(prev_row) if prev_row else None
    
    # Extract Oura metrics
    readiness = latest.get("readiness")
    hrv = latest.get("hrv")
    resting_hr = latest.get("resting_hr")
    body_temp = latest.get("body_temp_deviation")
    sleep_score = latest.get("sleep_score")
    sleep_hours = latest.get("sleep_hours")
    
    # Calculate trends
    trend = get_wellness_trend(days=7)
    
    # Determine health status
    status = "normal"
    status_emoji = "🟢"
    alerts = []
    
    if readiness is not None:
        if readiness < 60:
            status = "critical"
            status_emoji = "🔴"
            alerts.append(f"恢复分数极低 ({readiness})，建议完全休息")
        elif readiness < 70:
            status = "warning"
            status_emoji = "🟡"
            alerts.append(f"恢复分数偏低 ({readiness})，建议轻松活动")
    
    if hrv is not None and previous and previous.get("hrv"):
        hrv_drop = previous["hrv"] - hrv
        if hrv_drop > 10:
            alerts.append(f"HRV 下降 {hrv_drop:.1f}ms，自主神经压力增大")
    
    if body_temp is not None:
        if body_temp > 0.5:
            alerts.append(f"体温偏高 (+{body_temp:.2f}°C)，可能处于炎症/感染状态")
        elif body_temp < -0.5:
            alerts.append(f"体温偏低 ({body_temp:.2f}°C)，注意保暖")
    
    # Build summary
    summary = {
        "has_data": True,
        "date": current_date,
        "status": status,
        "status_emoji": status_emoji,
        
        # Core Oura metrics
        "readiness": {
            "value": readiness,
            "vs_yesterday": previous.get("readiness") if previous else None,
            "indicator": _get_indicator(readiness, previous.get("readiness") if previous else None),
        },
        "hrv": {
            "value": hrv,
            "vs_yesterday": previous.get("hrv") if previous else None,
            "indicator": _get_indicator(hrv, previous.get("hrv") if previous else None),
        },
        "resting_hr": {
            "value": resting_hr,
            "vs_yesterday": previous.get("resting_hr") if previous else None,
            "indicator": _get_indicator(resting_hr, previous.get("resting_hr") if previous else None, lower_is_better=True),
        },
        "body_temp": {
            "value": body_temp,
            "vs_yesterday": previous.get("body_temp_deviation") if previous else None,
            "indicator": "🌡️" if body_temp else "",
        },
        "sleep": {
            "score": sleep_score,
            "hours": sleep_hours,
        },
        
        # Analysis
        "alerts": alerts,
        "trend": trend,
    }
    
    return summary


def format_morning_health_text(summary: Dict[str, Any]) -> str:
    """Format health summary as readable text for reports."""
    if not summary.get("has_data"):
        return f"\n{'='*60}\n📊 Oura 晨间健康综述\n{'='*60}\n{summary.get('message', '暂无数据')}\n"
    
    lines = [
        "",
        "=" * 60,
        f"📊 Oura 晨间健康综述 {summary['status_emoji']}",
        f"日期: {summary['date']}",
        "=" * 60,
        "",
    ]
    
    # Readiness
    r = summary.get("readiness", {})
    if r.get("value"):
        vs_text = f" (vs 昨日: {r['vs_yesterday']:.0f} {r['indicator']})" if r.get("vs_yesterday") else ""
        lines.append(f"🎯 恢复分数 (Readiness): {r['value']:.0f}{vs_text}")
    
    # HRV
    h = summary.get("hrv", {})
    if h.get("value"):
        vs_text = f" (vs 昨日: {h['vs_yesterday']:.1f} {h['indicator']})" if h.get("vs_yesterday") else ""
        lines.append(f"💓 HRV: {h['value']:.1f} ms{vs_text}")
    
    # Resting HR
    hr = summary.get("resting_hr", {})
    if hr.get("value"):
        vs_text = f" (vs 昨日: {hr['vs_yesterday']:.0f} {hr['indicator']})" if hr.get("vs_yesterday") else ""
        lines.append(f"❤️ 静息心率: {hr['value']:.0f} bpm{vs_text}")
    
    # Body Temp
    t = summary.get("body_temp", {})
    if t.get("value"):
        temp_val = t['value']
        temp_str = f"+{temp_val:.2f}" if temp_val > 0 else f"{temp_val:.2f}"
        lines.append(f"🌡️ 体温偏差: {temp_str}°C {t['indicator']}")
    
    # Sleep
    s = summary.get("sleep", {})
    if s.get("score") or s.get("hours"):
        sleep_parts = []
        if s.get("score"):
            sleep_parts.append(f"评分 {s['score']:.0f}")
        if s.get("hours"):
            sleep_parts.append(f"时长 {s['hours']:.1f}h")
        lines.append(f"🛌 睡眠: {' / '.join(sleep_parts)}")
    
    # Alerts
    if summary.get("alerts"):
        lines.append("")
        lines.append("⚠️ 健康提醒:")
        for alert in summary["alerts"]:
            lines.append(f"   • {alert}")
    
    # Training recommendation
    lines.append("")
    lines.append("💡 今日训练建议:")
    
    readiness_val = summary.get("readiness", {}).get("value", 70)
    if readiness_val >= 85:
        lines.append("   • 恢复状态优秀，可正常进行高强度训练")
    elif readiness_val >= 70:
        lines.append("   • 恢复状态良好，可进行中等强度训练")
    elif readiness_val >= 60:
        lines.append("   • 恢复状态一般，建议低强度有氧或休息")
    else:
        lines.append("   • 恢复状态较差，强烈建议完全休息")
    
    if summary.get("body_temp", {}).get("value", 0) > 0.3:
        lines.append("   • 体温偏高，避免高强度训练，注意补水")
    
    lines.append("")
    lines.append("=" * 60)
    lines.append("")
    
    return "\n".join(lines)


def get_morning_health_report() -> str:
    """Get formatted morning health report for display."""
    summary = generate_morning_health_summary()
    return format_morning_health_text(summary)


# ═══════════════════════════════════════════════════════════════════════════════
# Integration with Activity Reports
# ═══════════════════════════════════════════════════════════════════════════════

def prepend_to_cycling_report(report_text: str) -> str:
    """Prepend Oura health summary to a cycling analysis report."""
    health_report = get_morning_health_report()
    return health_report + report_text
