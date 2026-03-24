"""
Website crawler — uses Playwright (headless Chromium) to render JS-heavy clinic
websites, then extracts text from the most relevant pages.

Strategy:
  1. Prime cookies by visiting the homepage first.
  2. Proactively attempt a curated list of common paths (providers, team, contact…).
  3. Also score and follow links discovered on the homepage.
  4. Return combined plain text for the AI extractor.
"""

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Paths we always try, in priority order
PRIORITY_PATHS = [
    "/providers", "/provider", "/our-providers", "/our-team", "/meet-our-team",
    "/team", "/doctors", "/doctor", "/physician", "/physicians", "/staff",
    "/therapists", "/clinicians", "/practitioners", "/specialists",
    "/about", "/about-us", "/meet-the-team",
    "/contact", "/contact-us",
]

# Extra keywords for scoring links discovered during crawl
PROVIDER_KEYWORDS = [
    "team", "doctor", "provider", "physician", "staff", "specialist",
    "faculty", "clinician", "therapist", "psychiatrist", "psychologist",
    "counselor", "practitioner", "bio", "profile", "meet",
    "contact",
]


def _normalise(url: str) -> str:
    return url.split("#")[0].split("?")[0].rstrip("/")


def _same_domain(base: str, link: str) -> bool:
    return urlparse(base).netloc == urlparse(link).netloc


def _extract_text_and_links(html: str, base_url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript", "svg", "img", "header"]):
        tag.decompose()
    text = re.sub(r"\s{3,}", "\n\n", soup.get_text(separator="\n")).strip()
    links: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = urljoin(base_url, a["href"])
        if href.startswith("http") and _same_domain(base_url, href):
            links.add(_normalise(href))
    return {"text": text, "links": links}


def crawl_website(base_url: str, max_extra_pages: int = 6) -> str:
    """Return combined text from the clinic website using a headless browser."""
    if not base_url.startswith("http"):
        base_url = "https://" + base_url
    base_url = _normalise(base_url)
    origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"

    from playwright.sync_api import sync_playwright

    pages: list[str] = []
    visited: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            java_script_enabled=True,
        )
        page = ctx.new_page()

        def _fetch(url: str) -> dict | None:
            url = _normalise(url)
            if url in visited:
                return None
            try:
                resp = page.goto(url, wait_until="networkidle", timeout=25000)
                if not resp or resp.status >= 400:
                    return None
                page.wait_for_timeout(1000)
                result = _extract_text_and_links(page.content(), url)
                if len(result["text"]) < 80:   # still looks like a shell — skip
                    return None
                visited.add(url)
                return result
            except Exception:
                return None

        # ── 1. Homepage first (primes cookies / session) ──────────
        home = _fetch(base_url)
        if home:
            pages.append(f"=== HOME ({base_url}) ===\n{home['text']}")
            discovered_links = home["links"]
        else:
            discovered_links = set()

        # ── 2. Proactively try priority paths ─────────────────────
        for path in PRIORITY_PATHS:
            url = origin + path
            if _normalise(url) in visited:
                continue
            result = _fetch(url)
            if result:
                pages.append(f"=== {url} ===\n{result['text']}")
                discovered_links |= result["links"]

        # ── 3. Score & follow remaining discovered links ──────────
        scored: list[tuple[int, str]] = []
        for link in discovered_links:
            if link in visited:
                continue
            link_path = urlparse(link).path.lower()
            score = sum(kw in link_path for kw in PROVIDER_KEYWORDS)
            if score:
                scored.append((score, link))

        scored.sort(reverse=True)
        extra = 0
        for _, link in scored:
            if extra >= max_extra_pages:
                break
            result = _fetch(link)
            if result:
                pages.append(f"=== {link} ===\n{result['text']}")
                extra += 1

        browser.close()

    return "\n\n".join(pages)
