#!/usr/bin/env python3
"""
ti_catalog.py -- List course groups from the TI catalog.

Usage:
    python ti_catalog.py
    python ti_catalog.py --search <keyword>
    python ti_catalog.py --limit <N>
"""

import argparse
import sys
import time
from pathlib import Path

# -- Bootstrap: add plugin root to path for lib imports ------------------------
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import resolve_credentials

# -- Dependencies --------------------------------------------------------------
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests",
                           "--break-system-packages", "-q"])
    import requests


def _unwrap(data) -> list:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for k in ("courseGroups", "data", "items", "results"):
            if k in data and isinstance(data[k], list):
                return data[k]
    return []


def main():
    parser = argparse.ArgumentParser(description="Browse the TI course catalog")
    parser.add_argument("--search", help="Filter by title keyword (case-insensitive)")
    parser.add_argument(
        "--limit", type=int, default=250,
        help="Max courses to fetch (default 250). Uses cursor-based pagination."
    )
    args = parser.parse_args()

    creds = resolve_credentials()
    base_url = creds["base_url"].rstrip("/")
    api_key = creds["api_key"]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    all_groups = []
    cursor = None

    while len(all_groups) < args.limit:
        params = {"per_page": 50}
        if cursor:
            params["cursor"] = cursor

        resp = requests.get(
            f"{base_url}/incoming/v2/courseGroups",
            headers=headers,
            params=params,
            timeout=30,
        )

        # Respect rate limit
        if resp.status_code == 429:
            reset_at = int(resp.headers.get("X-RateLimit-Reset", 0))
            wait = max(1, reset_at - int(time.time()))
            print(f"Rate limited -- waiting {wait}s before retrying...")
            time.sleep(wait)
            continue

        if resp.status_code != 200:
            print(f"[ERROR] {resp.status_code}: {resp.text[:200]}")
            sys.exit(1)

        body = resp.json()
        items = _unwrap(body)
        if not items:
            break
        all_groups.extend(items)

        page_info = body.get("pageInfo", {})
        has_more = page_info.get("hasMore", False)
        cursor = page_info.get("cursor")

        if not has_more or not cursor:
            break

    keyword = (args.search or "").lower()
    results = [
        cg for cg in all_groups
        if not keyword or keyword in cg.get("title", "").lower()
    ]

    label = f"matching '{args.search}'" if args.search else f"(fetched {len(all_groups)} total)"
    print(f"Found {len(results)} course group(s) {label}:\n")

    for cg in results:
        cg_id = cg.get("id", "")
        title = cg.get("title", "")
        slug = cg.get("slug", "")
        status = cg.get("status", "")
        courses = cg.get("courses", [])
        course_ids = [c.get("id", "") for c in courses if c.get("id")]

        print(f"  {title}")
        print(f"    slug:      {slug}")
        print(f"    id:        {cg_id}")
        if course_ids:
            for i, cid in enumerate(course_ids):
                print(f"    course_id{'' if len(course_ids) == 1 else f'[{i}]'}: {cid}")
        if status:
            print(f"    status:    {status}")
        print()


if __name__ == "__main__":
    main()
