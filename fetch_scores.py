#!/usr/bin/env python3
"""
PayPal Trustpilot Score Fetcher
Runs daily via GitHub Actions to update data.json with latest scores.
"""

import json
import os
import sys
from datetime import date, datetime, timezone

import requests
from bs4 import BeautifulSoup

# ── Locale config ─────────────────────────────────────────────────────────────
LOCALES = {
    "fr": {
        "name": "France",
        "flag": "🇫🇷",
        "url": "https://www.trustpilot.com/review/www.paypal.fr",
        "baseline": 1.5,
    },
    "es": {
        "name": "Spain",
        "flag": "🇪🇸",
        "url": "https://www.trustpilot.com/review/www.paypal.es",
        "baseline": 1.5,
    },
    "uk": {
        "name": "United Kingdom",
        "flag": "🇬🇧",
        "url": "https://www.trustpilot.com/review/www.paypal.com/gb",
        "baseline": 1.2,
    },
    "it": {
        "name": "Italy",
        "flag": "🇮🇹",
        "url": "https://www.trustpilot.com/review/paypal.com/it",
        "baseline": 3.7,
    },
}

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}


# ── Scraper ───────────────────────────────────────────────────────────────────
def fetch_trustpilot(url: str) -> tuple[float | None, int | None]:
    """
    Fetch TrustScore and total review count from a Trustpilot business page.
    Returns (score, review_count) or (None, None) on failure.
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"    ❌ HTTP error: {e}")
        return None, None

    soup = BeautifulSoup(resp.text, "lxml")
    score, reviews = None, None

    # ── Method 1: JSON-LD structured data (most reliable) ────────────────────
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            payload = json.loads(script.string or "")
            if isinstance(payload, list):
                payload = next(
                    (p for p in payload if p.get("@type") == "Organization"), None
                )
            if payload and "aggregateRating" in payload:
                ar = payload["aggregateRating"]
                score = round(float(ar["ratingValue"]), 1)
                reviews = int(ar["reviewCount"])
                break
        except Exception:
            continue

    # ── Method 2: Next.js __NEXT_DATA__ hydration blob ───────────────────────
    if score is None:
        nd_tag = soup.find("script", id="__NEXT_DATA__")
        if nd_tag:
            try:
                nd = json.loads(nd_tag.string or "")
                biz = nd["props"]["pageProps"]["businessUnit"]
                score = round(float(biz["trustScore"]), 1)
                reviews = int(biz["numberOfReviews"]["total"])
            except Exception:
                pass

    # ── Method 3: meta tags fallback ─────────────────────────────────────────
    if score is None:
        m_score = soup.find("meta", {"name": "trustpilot-starscore"})
        m_reviews = soup.find("meta", {"name": "trustpilot-reviewcount"})
        if m_score:
            score = round(float(m_score.get("content", 0)), 1)
        if m_reviews:
            reviews = int(m_reviews.get("content", 0))

    return score, reviews


# ── Data helpers ─────────────────────────────────────────────────────────────
def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            return json.load(f)
    # Bootstrap from LOCALES config
    return {
        "last_updated": None,
        "locales": {
            k: {
                "name": v["name"],
                "flag": v["flag"],
                "url": v["url"],
                "baseline": v["baseline"],
                "data": [],
            }
            for k, v in LOCALES.items()
        },
    }


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    today = date.today().isoformat()
    data = load_data()
    any_success = False
    errors = []

    for loc_key, loc_info in LOCALES.items():
        print(f"\n🔍 {loc_info['flag']} {loc_info['name']}  →  {loc_info['url']}")
        score, reviews = fetch_trustpilot(loc_info["url"])

        if score is None:
            msg = f"{loc_info['name']}: could not fetch score"
            print(f"    ⚠️  {msg}")
            errors.append(msg)
            continue

        # Calculate reviews/day delta
        locale_pts = data["locales"][loc_key]["data"]
        rev_per_day = None
        if reviews and locale_pts:
            last = locale_pts[-1]
            if last.get("reviews"):
                days = (
                    date.fromisoformat(today) - date.fromisoformat(last["date"])
                ).days
                if days > 0:
                    rev_per_day = round((reviews - last["reviews"]) / days)

        # Upsert today's entry
        existing = next((d for d in locale_pts if d["date"] == today), None)
        if existing:
            existing.update(
                {"score": score, "reviews": reviews, "reviews_per_day": rev_per_day}
            )
            print(f"    ✅ Updated  {today}  score={score}  reviews={reviews}  rev/day={rev_per_day}")
        else:
            locale_pts.append(
                {
                    "date": today,
                    "score": score,
                    "reviews": reviews,
                    "reviews_per_day": rev_per_day,
                }
            )
            print(f"    ✅ Inserted {today}  score={score}  reviews={reviews}  rev/day={rev_per_day}")

        any_success = True

    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    save_data(data)

    print(f"\n{'✅' if any_success else '❌'} data.json saved  ({today})")
    if errors:
        print("⚠️  Partial failures:")
        for e in errors:
            print(f"   • {e}")

    # Exit non-zero only if ALL locales failed
    if not any_success:
        sys.exit(1)


if __name__ == "__main__":
    main()
