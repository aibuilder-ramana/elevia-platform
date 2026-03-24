from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

from crawler import crawl_website
from extractor import extract_clinic_data
from database import save_clinic_with_providers, update_clinic_kb_path, get_clinic
from knowledge_base import write_intake_kb, read_intake_kb

app = FastAPI(title="Elevia Clinic Onboarder")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.mount("/static", StaticFiles(directory="static"), name="static")


class CrawlRequest(BaseModel):
    clinic_name: str
    website_url: str


class SaveRequest(BaseModel):
    clinic: dict[str, Any]
    providers: list[dict[str, Any]]
    intake: dict[str, Any] = {}


class IntakeUpdateRequest(BaseModel):
    intake: dict[str, Any]


@app.get("/", response_class=HTMLResponse)
def root():
    with open("static/index.html") as f:
        return f.read()


@app.post("/crawl")
def crawl(req: CrawlRequest):
    try:
        raw = crawl_website(req.website_url)
        if not raw:
            raise HTTPException(status_code=422, detail="Could not fetch website content.")
        data = extract_clinic_data(req.clinic_name, req.website_url, raw)
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/save")
def save(req: SaveRequest):
    try:
        result = save_clinic_with_providers(req.clinic, req.providers)
        clinic_id   = result["clinic_id"]
        clinic_name = req.clinic.get("name", "")
        if req.intake:
            kb_path = write_intake_kb(clinic_id, clinic_name, req.intake)
            update_clinic_kb_path(clinic_id, kb_path)
            result["kb_path"] = kb_path
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/clinics/{clinic_id}/intake")
def api_clinic_intake(clinic_id: int):
    records = read_intake_kb(clinic_id)
    if not records:
        raise HTTPException(status_code=404, detail="No intake profile found for this clinic.")
    return records


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
