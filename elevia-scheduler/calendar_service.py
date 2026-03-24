from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime, timedelta
from config import GOOGLE_CREDENTIALS_FILE, CALENDAR_ID

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        GOOGLE_CREDENTIALS_FILE,
        scopes=SCOPES,
    )
    return build("calendar", "v3", credentials=creds)


def create_event(
    patient_name: str,
    start_time: str,
    description: str = "",
    provider_email: str = None,
    patient_email: str = None,
) -> str:
    service = get_calendar_service()

    start = datetime.fromisoformat(start_time)
    end = start + timedelta(minutes=30)

    attendees = []
    if provider_email:
        attendees.append({"email": provider_email, "displayName": "Provider"})
    if patient_email:
        attendees.append({"email": patient_email, "displayName": patient_name})

    event = {
        "summary": f"Appointment with {patient_name}",
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": "America/New_York"},
        "end":   {"dateTime": end.isoformat(),   "timeZone": "America/New_York"},
        "attendees": attendees,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email",  "minutes": 1440},
                {"method": "popup",  "minutes": 30},
            ],
        },
    }

    created = service.events().insert(
        calendarId=CALENDAR_ID,
        body=event,
        sendUpdates="all",
    ).execute()

    return created["id"]
