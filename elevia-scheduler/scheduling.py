from datetime import datetime, timedelta
from typing import List


def get_available_slots(date: str, interval_minutes: int = 30) -> List[str]:
    """Generate available time slots for a given date (9 AM – 5 PM)."""
    start = datetime.fromisoformat(f"{date}T09:00")
    end   = datetime.fromisoformat(f"{date}T17:00")
    slots = []
    current = start
    while current < end:
        slots.append(current.strftime("%Y-%m-%dT%H:%M"))
        current += timedelta(minutes=interval_minutes)
    return slots
