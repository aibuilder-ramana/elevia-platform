from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

from database import (
    list_clinics, get_clinic,
    update_clinic_kb_path, update_clinic, update_provider,
    delete_provider, delete_clinic, get_clinic_id_by_provider_id,
)
from knowledge_base import write_intake_kb, read_intake_kb

app = FastAPI(title="Elevia Admin Portal")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html") as f:
        return f.read()


# ── Clinic read routes ────────────────────────────────────

@app.get("/api/clinics")
def api_clinics(q: str = ""):
    return list_clinics(q)


@app.get("/api/clinics/{clinic_id}")
def api_clinic(clinic_id: int):
    data = get_clinic(clinic_id)
    if not data:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return data


# ── Intake routes ─────────────────────────────────────────

@app.get("/api/clinics/{clinic_id}/intake")
def api_clinic_intake(clinic_id: int):
    records = read_intake_kb(clinic_id)
    if not records:
        raise HTTPException(status_code=404, detail="No intake profile found for this clinic.")
    return records


class IntakeUpdateRequest(BaseModel):
    intake: dict[str, Any]


@app.patch("/api/clinics/{clinic_id}/intake")
def api_update_intake(clinic_id: int, req: IntakeUpdateRequest):
    try:
        data = get_clinic(clinic_id)
        if not data:
            raise HTTPException(status_code=404, detail="Clinic not found")
        kb_path = write_intake_kb(clinic_id, data["clinic"]["name"], req.intake)
        update_clinic_kb_path(clinic_id, kb_path)
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Provider intake lookup (used by elevia-agent) ─────────

@app.get("/api/providers/{provider_id}/intake")
def api_provider_intake(provider_id: str):
    clinic_id = get_clinic_id_by_provider_id(provider_id)
    if not clinic_id:
        return []
    return read_intake_kb(clinic_id)


# ── Clinic / provider update + delete routes ──────────────

class ClinicUpdateRequest(BaseModel):
    fields: dict[str, Any]


class ProviderUpdateRequest(BaseModel):
    fields: dict[str, Any]


@app.patch("/api/clinics/{clinic_id}")
def api_update_clinic(clinic_id: int, req: ClinicUpdateRequest):
    try:
        update_clinic(clinic_id, req.fields)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/clinics/{clinic_id}")
def api_delete_clinic(clinic_id: int):
    try:
        delete_clinic(clinic_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/api/providers/{provider_id}")
def api_update_provider(provider_id: int, req: ProviderUpdateRequest):
    try:
        update_provider(provider_id, req.fields)
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/providers/{provider_id}")
def api_delete_provider(provider_id: int):
    try:
        delete_provider(provider_id)
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
