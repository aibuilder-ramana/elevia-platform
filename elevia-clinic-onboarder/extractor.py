"""
Claude-powered extractor — turns raw crawled text into structured
clinic + provider data.
"""
import os
import json
import re
from anthropic import Anthropic

PROMPT = """You are a medical data extraction specialist.
Extract structured information from the clinic website content below.

Clinic Name (user-supplied): {clinic_name}
Website: {website}

Website Content:
---
{content}
---

Return ONLY a valid JSON object — no markdown, no explanation — with this exact structure:

{{
  "clinic": {{
    "name": "full clinic name",
    "address": "full street address, city, state, zip",
    "phone": "main phone number",
    "email": "main email or null",
    "website": "{website}",
    "specialties": ["specialty1","specialty2","specialty3","specialty4","specialty5"]
  }},
  "providers": [
    {{
      "name": "Dr. Full Name",
      "title": "MD / LCSW / PsyD / etc.",
      "years_of_practice": "number or null",
      "specializations": ["spec1","spec2","spec3","spec4","spec5"],
      "accepting_new_patients": true,
      "phone": "direct phone or null",
      "rating": null,
      "reviews": null,
      "description": "1-2 sentence bio if available, else null"
    }}
  ]
}}

Rules:
- Extract ALL providers/doctors/therapists/clinicians found on the site.
- For specialties/specializations, list up to 5 most prominent.
- Use null for any field not found — never guess.
- accepting_new_patients: true if mentioned, false if stated as not accepting, null if unknown.
- Return an empty providers array [] if no individual providers are listed.
"""


def extract_clinic_data(clinic_name: str, website: str, raw_content: str) -> dict:
    """Call Claude to extract structured clinic + provider data from raw crawled text."""
    client = Anthropic()  # reads ANTHROPIC_API_KEY from environment
    content = raw_content[:60_000]

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                clinic_name=clinic_name,
                website=website,
                content=content,
            ),
        }],
    )

    text = response.content[0].text.strip()

    # Strip any accidental markdown fences
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to extract first JSON object
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group())
        return {"clinic": {}, "providers": [], "error": "Extraction failed — could not parse JSON."}
