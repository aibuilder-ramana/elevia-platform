from typing import List, Optional
from providers import load_providers

STATE_ABBREVS = {
    "al":"alabama","ak":"alaska","az":"arizona","ar":"arkansas","ca":"california",
    "co":"colorado","ct":"connecticut","de":"delaware","fl":"florida","ga":"georgia",
    "hi":"hawaii","id":"idaho","il":"illinois","in":"indiana","ia":"iowa","ks":"kansas",
    "ky":"kentucky","la":"louisiana","me":"maine","md":"maryland","ma":"massachusetts",
    "mi":"michigan","mn":"minnesota","ms":"mississippi","mo":"missouri","mt":"montana",
    "ne":"nebraska","nv":"nevada","nh":"new hampshire","nj":"new jersey","nm":"new mexico",
    "ny":"new york","nc":"north carolina","nd":"north dakota","oh":"ohio","ok":"oklahoma",
    "or":"oregon","pa":"pennsylvania","ri":"rhode island","sc":"south carolina",
    "sd":"south dakota","tn":"tennessee","tx":"texas","ut":"utah","vt":"vermont",
    "va":"virginia","wa":"washington","wv":"west virginia","wi":"wisconsin","wy":"wyoming",
}

def _normalize_location(location: str) -> str:
    """Expand state abbreviations so 'Orange, CT' matches 'Orange, Connecticut'."""
    parts = [p.strip() for p in location.replace(",", " ").split()]
    expanded = [STATE_ABBREVS.get(p.lower(), p) for p in parts]
    return " ".join(expanded).lower()


def get_all_providers() -> List[dict]:
    return load_providers()


def get_provider_by_id(provider_id: str) -> Optional[dict]:
    return next((p for p in load_providers() if p["provider_id"] == provider_id), None)


def search_providers(
    issue: Optional[str] = None,
    insurance: Optional[str] = None,
    location: Optional[str] = None,
    accepting_only: bool = True,
    limit: int = 10,
) -> List[dict]:
    results = load_providers()

    if accepting_only:
        results = [p for p in results if p.get("accepting_new_patients")]

    if insurance:
        results = [
            p for p in results
            if any(insurance.lower() in ins.lower() for ins in p.get("insurance", []))
        ]

    if location:
        normalized = _normalize_location(location)
        results = [
            p for p in results
            if p["contact"].get("mailing_address")
            and any(word in p["contact"]["mailing_address"].lower() for word in normalized.split())
        ]

    if issue:
        issue_lower = issue.lower()
        results = sorted(
            results,
            key=lambda p: issue_lower in p.get("specializations", "").lower(),
            reverse=True,
        )

    results = sorted(results, key=lambda p: (p["rating"], p["reviews"]), reverse=True)

    return results[:limit]
