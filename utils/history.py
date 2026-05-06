"""
utils/history.py — helpers for grouping raw chat_history into conversations.
"""
from collections import OrderedDict
from datetime import datetime


def group_by_session(history: list) -> list:
    """
    Group chat_history entries by session_id.
    Old entries without session_id are grouped by date (backward-compat).
    Replaces the old _group_by_session / _group_by_date alias pair.
    """
    groups: dict = OrderedDict()
    for entry in history:
        ts         = entry.get("timestamp", "")
        session_id = entry.get("session_id") or ("date:" + (ts[:10] if ts else "unknown"))
        if session_id not in groups:
            groups[session_id] = {
                "session_id": session_id,
                "label"     : _session_label(ts),
                "date"      : ts[:10] if ts else "Unknown",
                "messages"  : [],
            }
        groups[session_id]["messages"].append({
            "user"     : entry.get("user", ""),
            "arjun"    : entry.get("arjun", ""),
            "timestamp": ts,
        })
    return list(groups.values())


def _session_label(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y · %I:%M %p").lstrip("0")
    except Exception:
        return ts[:16] if ts else "Unknown"
