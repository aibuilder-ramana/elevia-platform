from pydantic import BaseModel
from typing import Optional


class Appointment(BaseModel):
    provider_id: str
    patient_name: str
    patient_email: str
    time: str                    # ISO datetime e.g. "2026-03-20T09:30"
    insurance_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    issue: Optional[str] = None
    notes: Optional[str] = None
