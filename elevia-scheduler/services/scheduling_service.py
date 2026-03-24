from services.provider_service import get_provider_by_id
from calendar_service import create_event
from models.appointment import Appointment


def schedule(appt: Appointment) -> dict:
    provider = get_provider_by_id(appt.provider_id)
    if not provider:
        return {"status": "error", "message": f"Provider '{appt.provider_id}' not found."}

    lines = [
        "── Patient Information ──────────────────────",
        f"Name:         {appt.patient_name}",
        f"Email:        {appt.patient_email}",
        f"Date of Birth:{appt.date_of_birth or 'Not provided'}",
        f"Insurance ID: {appt.insurance_id or 'Not provided'}",
        f"Issue:        {appt.issue or 'Not specified'}",
    ]

    if appt.notes and appt.notes.strip():
        lines += ["", "── Clinical Screening Results ───────────────", appt.notes.strip()]

    description = "\n".join(lines)

    provider_email = provider.get("contact", {}).get("email") or None

    try:
        event_id = create_event(
            patient_name=appt.patient_name,
            start_time=appt.time,
            description=description,
            provider_email=provider_email,
            patient_email=appt.patient_email,
        )
    except ValueError:
        return {
            "status": "error",
            "message": (
                f"Invalid appointment time '{appt.time}'. "
                "Please provide an exact date and time in ISO format, e.g. 2026-03-20T09:30."
            ),
        }

    return {"status": "confirmed", "event_id": event_id, "provider": provider["provider_name"]}
