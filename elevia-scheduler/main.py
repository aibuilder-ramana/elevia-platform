from fastapi import FastAPI, HTTPException
from models.appointment import Appointment
from services.provider_service import get_all_providers, get_provider_by_id, search_providers
from services.scheduling_service import schedule
from scheduling import get_available_slots

app = FastAPI(title="elevia-scheduler")


@app.get("/providers")
def list_providers(issue: str = "", insurance: str = "", location: str = "", limit: int = 10):
    """Search or list all providers."""
    if issue or insurance or location:
        results = search_providers(
            issue=issue or None,
            insurance=insurance or None,
            location=location or None,
            limit=limit,
        )
    else:
        results = get_all_providers()[:limit]
    return {"providers": results}


@app.get("/providers/{provider_id}")
def provider_detail(provider_id: str):
    """Get full details for a single provider."""
    provider = get_provider_by_id(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return provider


@app.get("/availability/{provider_id}")
def get_availability(provider_id: str, date: str = "2026-03-20"):
    """Return available appointment slots for a provider on a given date."""
    provider = get_provider_by_id(provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail=f"Provider '{provider_id}' not found.")
    return {"provider_id": provider_id, "date": date, "slots": get_available_slots(date)}


@app.post("/schedule")
def schedule_appointment(appt: Appointment):
    """Book an appointment and create a Google Calendar event."""
    result = schedule(appt)
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])
    return result
