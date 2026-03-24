import os
import re
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://swapna@localhost:5432/elevia_platform")
engine = create_engine(DATABASE_URL)


# ── Read operations ───────────────────────────────────────

def list_clinics(search: str = "") -> list[dict]:
    q = f"%{search.lower()}%"
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT c.id, c.name, c.address, c.phone, c.website, c.email, c.created_at,
                   COUNT(p.id) AS provider_count
            FROM clinics c
            LEFT JOIN providers p ON p.clinic_id = c.id
            WHERE LOWER(c.name) LIKE :q OR LOWER(c.address) LIKE :q OR LOWER(c.website) LIKE :q
            GROUP BY c.id
            ORDER BY c.created_at DESC
        """), {"q": q}).mappings().all()
    return [dict(r) for r in rows]


def get_clinic(clinic_id: int) -> dict | None:
    with engine.connect() as conn:
        clinic_row = conn.execute(text("""
            SELECT id, name, address, phone, email, website, mcp_endpoint, kb_path, created_at
            FROM clinics WHERE id = :id
        """), {"id": clinic_id}).mappings().first()

        if not clinic_row:
            return None

        provider_rows = conn.execute(text("""
            SELECT id, provider_id, name, specializations, description, phone,
                   mailing_address, insurance, accepting_new_patients,
                   rating, reviews, calendar_type, created_at
            FROM providers WHERE clinic_id = :id ORDER BY name
        """), {"id": clinic_id}).mappings().all()

    clinic = dict(clinic_row)
    clinic["created_at"] = str(clinic["created_at"])

    providers = []
    for p in provider_rows:
        d = dict(p)
        d["created_at"] = str(d["created_at"])
        d["specializations"] = [s.strip() for s in (d["specializations"] or "").split(",") if s.strip()]
        d["insurance"] = list(d["insurance"] or [])
        providers.append(d)

    return {"clinic": clinic, "providers": providers}


# ── Write operations ──────────────────────────────────────

def _slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value)
    return value[:120]


def save_clinic_with_providers(clinic: dict, providers: list) -> dict:
    """Upsert clinic and all providers into the database. Returns summary."""
    with engine.begin() as conn:
        existing = conn.execute(
            text("SELECT id FROM clinics WHERE website = :w"),
            {"w": clinic.get("website", "")},
        ).fetchone()

        if existing:
            clinic_id = existing[0]
            conn.execute(
                text("""
                    UPDATE clinics
                    SET name=:name, address=:address, phone=:phone, email=:email
                    WHERE id=:id
                """),
                {
                    "name":    clinic.get("name", ""),
                    "address": clinic.get("address", ""),
                    "phone":   clinic.get("phone", ""),
                    "email":   clinic.get("email"),
                    "id":      clinic_id,
                },
            )
        else:
            result = conn.execute(
                text("""
                    INSERT INTO clinics (name, address, website, phone, email)
                    VALUES (:name, :address, :website, :phone, :email)
                    RETURNING id
                """),
                {
                    "name":    clinic.get("name", ""),
                    "address": clinic.get("address", ""),
                    "website": clinic.get("website", ""),
                    "phone":   clinic.get("phone", ""),
                    "email":   clinic.get("email"),
                },
            )
            clinic_id = result.fetchone()[0]

        saved = 0
        skipped = 0
        for p in providers:
            provider_id = _slugify(f"{clinic.get('name','clinic')}-{p.get('name','unknown')}")
            specs = p.get("specializations", [])
            specs_str = ", ".join(specs) if isinstance(specs, list) else (specs or "")
            try:
                conn.execute(
                    text("""
                        INSERT INTO providers
                            (clinic_id, provider_id, name, specializations, description,
                             phone, accepting_new_patients, rating, reviews)
                        VALUES
                            (:clinic_id, :provider_id, :name, :specializations, :description,
                             :phone, :accepting, :rating, :reviews)
                        ON CONFLICT (provider_id) DO UPDATE
                            SET name=EXCLUDED.name,
                                specializations=EXCLUDED.specializations,
                                description=EXCLUDED.description,
                                phone=EXCLUDED.phone,
                                accepting_new_patients=EXCLUDED.accepting_new_patients,
                                rating=EXCLUDED.rating,
                                reviews=EXCLUDED.reviews
                    """),
                    {
                        "clinic_id":       clinic_id,
                        "provider_id":     provider_id,
                        "name":            p.get("name", ""),
                        "specializations": specs_str,
                        "description":     p.get("description"),
                        "phone":           p.get("phone"),
                        "accepting":       p.get("accepting_new_patients"),
                        "rating":          p.get("rating"),
                        "reviews":         p.get("reviews"),
                    },
                )
                saved += 1
            except Exception:
                skipped += 1

    return {
        "status":            "saved",
        "clinic_id":         clinic_id,
        "providers_saved":   saved,
        "providers_skipped": skipped,
    }


def update_clinic_kb_path(clinic_id: int, kb_path: str) -> None:
    """Store the path to the clinic's knowledge-base JSONL file."""
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE clinics SET kb_path = :kb_path WHERE id = :id"),
            {"kb_path": kb_path, "id": clinic_id},
        )


def update_clinic(clinic_id: int, fields: dict) -> None:
    allowed = {"name", "address", "phone", "email", "website", "mcp_endpoint"}
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in clean)
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE clinics SET {set_clause} WHERE id = :id"), {**clean, "id": clinic_id})


def update_provider(provider_id: int, fields: dict) -> None:
    allowed = {"name", "phone", "description", "accepting_new_patients", "rating", "reviews"}
    clean = {}
    for k, v in fields.items():
        if k not in allowed:
            continue
        if k == "accepting_new_patients" and isinstance(v, str):
            v = True if v == "true" else (False if v == "false" else None)
        clean[k] = v
    # specializations comes in as comma-string → store as-is (text column)
    if "specializations" in fields:
        specs = fields["specializations"]
        clean["specializations"] = specs if isinstance(specs, str) else ", ".join(specs)
    if not clean:
        return
    set_clause = ", ".join(f"{k} = :{k}" for k in clean)
    with engine.begin() as conn:
        conn.execute(text(f"UPDATE providers SET {set_clause} WHERE id = :id"), {**clean, "id": provider_id})


def delete_provider(provider_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM providers WHERE id = :id"), {"id": provider_id})


def delete_clinic(clinic_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM clinics WHERE id = :id"), {"id": clinic_id})


def get_clinic_id_by_provider_id(provider_id: str) -> int | None:
    """Return the clinic_id for a given provider_id slug, or None if not found."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT clinic_id FROM providers WHERE provider_id = :pid"),
            {"pid": provider_id},
        ).fetchone()
    return row[0] if row else None
