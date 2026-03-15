import json


def sse_event(event_type, data, event_id=None):
    """Format a Server-Sent Event message."""
    payload = json.dumps(data, ensure_ascii=False)
    parts = []
    if event_id is not None:
        parts.append(f"id: {event_id}")
    parts.append(f"event: {event_type}")
    parts.append(f"data: {payload}")
    return "\n".join(parts) + "\n\n"


def sse_keepalive():
    """Send a keepalive comment to prevent connection timeout."""
    return ": keepalive\n\n"
