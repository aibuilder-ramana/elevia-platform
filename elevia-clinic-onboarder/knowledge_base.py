"""
Clinic Knowledge Base
---------------------
Persists patient intake Q&A responses to:
  1. A per-clinic .jsonl file  → knowledge_base/clinic_{id}.jsonl
  2. ChromaDB collection       → 'clinic_intake'  (one doc per Q&A chunk)

Each JSONL line is a self-contained JSON object with all context needed
to reconstruct the screening profile without hitting the database.
"""

import json
from pathlib import Path
import chromadb

# ── Paths ─────────────────────────────────────────────────────────────────
KB_DIR        = Path(__file__).parent.parent / "knowledge_base"
CHROMA_DIR    = KB_DIR / ".chroma"
RESOURCES_DIR = Path(__file__).parent / "resources"
KB_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR.mkdir(parents=True, exist_ok=True)

# ── ChromaDB (lazy singleton) ──────────────────────────────────────────────
_collection = None

def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _collection = client.get_or_create_collection(
            name="clinic_intake",
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Legacy 18-question intake Q&A ─────────────────────────────────────────
# DISABLED: The clinic onboarding flow now uses structured patient intake form
# schemas (resources/*.json) selected per-clinic in step 4 of the UI.
# write_intake_kb() below is kept for backwards compatibility with any existing
# clinics that stored answers via the old flow, but is no longer called from
# the main onboarding path.
#
# QUESTION_META: list[tuple[str, str, str]] = [
#     ("telehealth",         "Practice Info",    "Does this clinic offer telehealth appointments?"),
#     ("states_licensed",    "Practice Info",    "Which U.S. states is the clinic licensed to serve patients in?"),
#     ("languages",          "Provider Details", "What languages do providers at this clinic speak?"),
#     ("specializations",    "Specializations",  "What mental health conditions does this clinic specialise in treating?"),
#     ("age_groups",         "Patient Criteria", "Which age groups does this clinic serve?"),
#     ("severity_levels",    "Patient Criteria", "What severity levels does this clinic typically accept?"),
#     ("exclusions",         "Patient Criteria", "Are there patient populations this clinic does NOT serve?"),
#     ("screening_tools",    "Screening",        "Which standardised screening tools does this clinic use?"),
#     ("si_handling",        "Risk Rules",       "How does this clinic handle active suicidal ideation at intake?"),
#     ("emergency_protocol", "Risk Rules",       "Does this clinic have a documented emergency / crisis protocol?"),
#     ("red_flags",          "Risk Rules",       "Which patient red flags should automatically exclude this clinic from matching?"),
#     ("modalities",         "Treatment",        "What treatment modalities do providers at this clinic use?"),
#     ("wait_time_days",     "Appointments",     "What is the typical new-patient wait time (in days)?"),
#     ("session_types",      "Appointments",     "What session formats does this clinic offer?"),
#     ("matching_criteria",  "Appointments",     "Which additional patient criteria does this clinic prioritise when matching?"),
#     ("insurance_plans",    "Insurance",        "Which insurance plans does this clinic accept?"),
#     ("self_pay",           "Insurance",        "Does this clinic accept self-pay (out-of-pocket) patients?"),
#     ("sliding_scale",      "Insurance",        "Is a sliding-scale fee structure available?"),
#     ("intake_notes",       "Additional Notes", "Any additional intake requirements or notes for the Elevia matching team?"),
# ]
QUESTION_META: list[tuple[str, str, str]] = []   # disabled — see above
_QUESTION_MAP: dict = {}


def _answer_display(val) -> str:
    """Convert a raw intake value to a human-readable string."""
    if val is True:
        return "Yes"
    if val is False:
        return "No"
    if isinstance(val, list):
        return ", ".join(str(v) for v in val) if val else "(none)"
    if val is None:
        return ""
    return str(val)


# ── Public API ────────────────────────────────────────────────────────────

def write_intake_kb(clinic_id: int, clinic_name: str, intake: dict) -> str:
    """
    Persist intake answers for a clinic.

    - Writes  knowledge_base/clinic_{clinic_id}.jsonl
    - Upserts one document per answered question into ChromaDB

    Returns the absolute path to the JSONL file.
    """
    kb_path = KB_DIR / f"clinic_{clinic_id}.jsonl"

    lines: list[str] = []
    docs:  list[str] = []
    metas: list[dict] = []
    ids:   list[str] = []

    for qid, section, question in QUESTION_META:
        if qid not in intake:
            continue
        val = intake[qid]
        display = _answer_display(val)
        if display == "" or display == "(none)":
            continue

        record = {
            "clinic_id":      clinic_id,
            "clinic_name":    clinic_name,
            "question_id":    qid,
            "section":        section,
            "question":       question,
            "answer":         val,
            "answer_display": display,
        }
        lines.append(json.dumps(record))

        # Chunk text for semantic search
        docs.append(f"[{section}] {question}\nAnswer: {display}")
        metas.append({
            "clinic_id":   clinic_id,
            "clinic_name": clinic_name,
            "question_id": qid,
            "section":     section,
        })
        ids.append(f"clinic_{clinic_id}_{qid}")

    # Write JSONL (overwrite on re-onboard)
    kb_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # Upsert into ChromaDB
    if docs:
        _get_collection().upsert(documents=docs, metadatas=metas, ids=ids)

    return str(kb_path)


def list_forms() -> list[dict]:
    """Return metadata for all available form schemas in resources/."""
    forms = []
    for path in sorted(RESOURCES_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            meta = data.get("metadata", {})
            forms.append({
                "form_id":      meta.get("form_id", path.stem),
                "title":        data.get("title", path.stem),
                "description":  meta.get("description", ""),
                "tags":         meta.get("tags", []),
                "medical_areas": meta.get("medical_areas", []),
            })
        except Exception:
            pass
    return forms


def write_forms_kb(clinic_id: int, clinic_name: str, form_ids: list[str]) -> None:
    """
    Link selected form schemas to a clinic.

    - Appends one record per form to knowledge_base/clinic_{id}.jsonl
    - Upserts a rich embedding document per form into ChromaDB
    """
    coll     = _get_collection()
    kb_path  = KB_DIR / f"clinic_{clinic_id}.jsonl"

    for fid in form_ids:
        form_path = RESOURCES_DIR / f"{fid}.json"
        if not form_path.exists():
            continue

        data  = json.loads(form_path.read_text(encoding="utf-8"))
        meta  = data.get("metadata", {})
        title = data.get("title", fid)
        desc  = meta.get("description", "")
        tags  = meta.get("tags", [])
        areas = meta.get("medical_areas", [])
        embed = meta.get(
            "embedding_text",
            f"{title}. {desc}. Tags: {', '.join(tags)}. Medical areas: {', '.join(areas)}.",
        )

        # Append to JSONL
        record = {
            "clinic_id":    clinic_id,
            "clinic_name":  clinic_name,
            "question_id":  f"form_{fid}",
            "section":      "Patient Intake Forms",
            "question":     f"Does this clinic use the form: {title}?",
            "answer":       True,
            "answer_display": f"Yes — {title}",
            "form_id":      fid,
            "form_title":   title,
            "form_tags":    tags,
            "form_areas":   areas,
        }
        with open(kb_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

        # Upsert into ChromaDB
        coll.upsert(
            documents=[embed],
            metadatas=[{
                "clinic_id":   clinic_id,
                "clinic_name": clinic_name,
                "question_id": f"form_{fid}",
                "section":     "Patient Intake Forms",
                "form_id":     fid,
            }],
            ids=[f"clinic_{clinic_id}_form_{fid}"],
        )


def read_intake_kb(clinic_id: int) -> list[dict]:
    """
    Read all Q&A records for a clinic from its JSONL file.
    Returns an empty list if the file does not exist.
    """
    kb_path = KB_DIR / f"clinic_{clinic_id}.jsonl"
    if not kb_path.exists():
        return []
    records = []
    for line in kb_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return records
