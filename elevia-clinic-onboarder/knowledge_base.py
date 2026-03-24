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
KB_DIR     = Path(__file__).parent.parent / "knowledge_base"
CHROMA_DIR = KB_DIR / ".chroma"
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


# ── Question registry (mirrors INTAKE_QUESTIONS in index.html) ────────────
QUESTION_META: list[tuple[str, str, str]] = [
    # (question_id, section, question_text)
    ("telehealth",         "Practice Info",    "Does this clinic offer telehealth appointments?"),
    ("states_licensed",    "Practice Info",    "Which U.S. states is the clinic licensed to serve patients in?"),
    ("languages",          "Provider Details", "What languages do providers at this clinic speak?"),
    ("specializations",    "Specializations",  "What mental health conditions does this clinic specialise in treating?"),
    ("age_groups",         "Patient Criteria", "Which age groups does this clinic serve?"),
    ("severity_levels",    "Patient Criteria", "What severity levels does this clinic typically accept?"),
    ("exclusions",         "Patient Criteria", "Are there patient populations this clinic does NOT serve?"),
    ("screening_tools",    "Screening",        "Which standardised screening tools does this clinic use?"),
    ("si_handling",        "Risk Rules",       "How does this clinic handle active suicidal ideation at intake?"),
    ("emergency_protocol", "Risk Rules",       "Does this clinic have a documented emergency / crisis protocol?"),
    ("red_flags",          "Risk Rules",       "Which patient red flags should automatically exclude this clinic from matching?"),
    ("modalities",         "Treatment",        "What treatment modalities do providers at this clinic use?"),
    ("wait_time_days",     "Appointments",     "What is the typical new-patient wait time (in days)?"),
    ("session_types",      "Appointments",     "What session formats does this clinic offer?"),
    ("matching_criteria",  "Appointments",     "Which additional patient criteria does this clinic prioritise when matching?"),
    ("insurance_plans",    "Insurance",        "Which insurance plans does this clinic accept?"),
    ("self_pay",           "Insurance",        "Does this clinic accept self-pay (out-of-pocket) patients?"),
    ("sliding_scale",      "Insurance",        "Is a sliding-scale fee structure available?"),
    ("intake_notes",       "Additional Notes", "Any additional intake requirements or notes for the Elevia matching team?"),
]

_QUESTION_MAP = {qid: (section, question) for qid, section, question in QUESTION_META}


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
