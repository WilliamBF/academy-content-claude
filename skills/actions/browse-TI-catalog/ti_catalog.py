#!/usr/bin/env python3
"""
ti_catalog.py -- List course groups from the TI catalog.

Uses GET /incoming/v2/content?types[]=courseGroups (100 rows/page, cursor
pagination, server-side search). The older /incoming/v2/courseGroups route
silently stops after 1,000 rows (page 21 returns an empty 200), so it is not used.

Usage:
    python ti_catalog.py
    python ti_catalog.py --search <keywords>
    python ti_catalog.py --text <keywords>    (all fields, not just title)
    python ti_catalog.py --query "level:Intermediate"
    python ti_catalog.py --status published
    python ti_catalog.py --limit <N>          (0 = no limit)
"""

import argparse
import re
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

MAX_RETRIES_429 = 5


class CatalogError(Exception):
    pass


def _get(url: str, headers: dict, params: dict):
    """GET with 429 handling (honours Retry-After). Returns the Response."""
    for _ in range(MAX_RETRIES_429):
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        if resp.status_code != 429:
            return resp
        wait = resp.headers.get("Retry-After")
        if wait and wait.isdigit():
            wait = int(wait)
        else:
            reset_at = int(resp.headers.get("X-RateLimit-Reset", 0) or 0)
            wait = max(1, reset_at - int(time.time())) if reset_at else 10
        print(f"Rate limited -- waiting {wait}s before retrying...", file=sys.stderr)
        time.sleep(wait + 1)
    raise CatalogError("Still rate limited after retries.")


def build_query(search: str, status: str, text: str = "", raw: str = "") -> str:
    """Build an OpenSearch query_string for the content endpoint.

    Each keyword becomes a lowercase prefix match on the analyzed (case-insensitive)
    title field; keywords are ANDed. Punctuation is stripped so it can't break the
    query syntax.
    """
    clauses = []
    words = re.findall(r"[A-Za-z0-9]+", search or "")
    if words:
        clauses.append("title.analyzed:(" + " AND ".join(f"{w.lower()}*" for w in words) + ")")
    if text:
        # Free text is searched across the whole document (title, description, slug,
        # tags, custom fields); terms are ANDed by the API.
        clauses.append(f"({text})")
    if raw:
        clauses.append(f"({raw})")
    if status:
        clauses.append(f"status:{status}")
    return " AND ".join(clauses)


def fetch_groups(base_url: str, headers: dict, query: str, limit: int):
    """Page through the catalog. Returns (groups, total, skipped, error_message_or_None).

    Whatever was fetched before an error is still returned. `skipped` counts null
    entries the API sometimes returns (stale index records) that were dropped.
    """
    groups, seen, total, cursor, skipped = [], set(), None, None, 0
    while not limit or len(groups) < limit:
        params = {"types[]": "courseGroups"}
        if query:
            params["query"] = query
        if cursor:
            params["cursor"] = cursor

        try:
            resp = _get(f"{base_url}/incoming/v2/content", headers, params)
        except (requests.RequestException, CatalogError) as e:
            return groups, total, skipped, str(e)
        if resp.status_code != 200:
            return groups, total, skipped, f"HTTP {resp.status_code}: {resp.text[:200]}"

        body = resp.json()
        # Malformed queries come back as HTTP 200 with a GraphQL error envelope.
        if "errors" in body or "pageInfo" not in body:
            return groups, total, skipped, f"API error (check the query): {str(body)[:200]}"

        for item in body.get("contentItems", []):
            if not isinstance(item, dict):
                skipped += 1
                continue
            if item.get("id") not in seen:
                seen.add(item.get("id"))
                groups.append(item)

        page_info = body["pageInfo"]
        total = page_info.get("total", total)
        cursor = page_info.get("cursor")
        if not page_info.get("hasMore") or not cursor:
            break

    if limit:
        groups = groups[:limit]
    return groups, total, skipped, None


def fetch_courses(base_url: str, headers: dict, group_id: str) -> list:
    """Course UUIDs for a group. /courses works for drafts; /displayCourse does not."""
    try:
        resp = _get(f"{base_url}/incoming/v2/courseGroups/{group_id}/courses", headers, {})
        if resp.status_code == 200:
            return resp.json().get("courses", [])
    except (requests.RequestException, CatalogError):
        pass
    return []


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    parser = argparse.ArgumentParser(description="Browse the TI course catalog")
    parser.add_argument("--search", help="Title keywords (case-insensitive, all must match; "
                                         "each matches as a word prefix)")
    parser.add_argument("--text", help="Free-text search across ALL fields (title, description, "
                                       "slug, tags, custom fields); terms are ANDed")
    parser.add_argument("--query", help="Raw OpenSearch query, e.g. 'level:Intermediate' or "
                                        "'slug.analyzed:meddpicc'; ANDed with the other filters")
    parser.add_argument("--status", choices=["published", "draft", "archived"],
                        help="Only list groups with this status (default: all)")
    parser.add_argument("--limit", type=int, default=250,
                        help="Max course groups to list (default 250, 0 = no limit)")
    parser.add_argument("--course-ids-max", type=int, default=15,
                        help="Look up course UUIDs only when this many groups or fewer are "
                             "listed (default 15; 0 = never). Each lookup is one API call.")
    args = parser.parse_args()

    creds = resolve_credentials()
    base_url = creds["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {creds['api_key']}", "Content-Type": "application/json"}

    query = build_query(args.search, args.status, args.text, args.query)
    groups, total, skipped, error = fetch_groups(base_url, headers, query, args.limit)

    terms = [t for t in (args.search, args.text, args.query) if t]
    qualifier = f" matching {' + '.join(repr(t) for t in terms)}" if terms else ""
    if args.status:
        qualifier += f" [{args.status}]"
    count_note = f" of {total}" if total is not None and total != len(groups) else ""
    print(f"Found {len(groups)}{count_note} course group(s){qualifier}:\n")

    lookup_ids = 0 < len(groups) <= args.course_ids_max

    for cg in groups:
        print(f"  {cg.get('title', '')}")
        print(f"    slug:      {cg.get('slug', '')}")
        print(f"    id:        {cg.get('id', '')}   (course group)")
        if lookup_ids:
            courses = fetch_courses(base_url, headers, cg.get("id", ""))
            for i, c in enumerate(courses):
                suffix = "" if len(courses) == 1 else f"[{i}]"
                print(f"    course_id{suffix}: {c.get('id', '')}")
            if not courses:
                print("    course_id: (none found)")
        if cg.get("status"):
            print(f"    status:    {cg['status']}")
        print()

    if not lookup_ids and groups:
        print(f"(Course UUIDs not looked up for {len(groups)} groups. Narrow with --search, "
              f"or raise --course-ids-max.)")
    if args.limit and total is not None and len(groups) < total and not error:
        print(f"(Showing {len(groups)} of {total}. Use --limit 0 for all, or --search/--status "
              f"to narrow.)")
    if skipped:
        print(f"(Skipped {skipped} empty record(s) returned by the API.)")
    if error:
        print(f"\n[ERROR] Stopped early after {len(groups)} group(s): {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
