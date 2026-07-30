#!/usr/bin/env python3
"""
ti_updater.py -- Targeted update of specific topics/lessons/sections in TI.

Usage:
  python ti_updater.py --payload update_payload.json
  python ti_updater.py --json '{"courseAttributes": {"topics": [{"id": "...", "body": "..."}]}}'
  python ti_updater.py --payload update_payload.json --dry-run

Payload shape:
  { "courseAttributes": { "topics": [{id, title?, body?, position?}] } }
  Sections and lessons are also valid keys inside courseAttributes.

All entities MUST include their UUID in the "id" field.
Run /extract-TI-course or /get-TI-course-structure first to find entity UUIDs.
"""

import argparse
import json
import sys
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


# -- Validation ----------------------------------------------------------------

def validate_payload(course_attributes: dict) -> list:
    """Return a list of validation error strings. Empty list means valid."""
    errors = []
    for entity_type in ("topics", "lessons", "sections"):
        for i, item in enumerate(course_attributes.get(entity_type, [])):
            if not item.get("id"):
                errors.append(
                    f"{entity_type}[{i}] (title: {item.get('title', '?')!r}) "
                    f"is missing 'id' UUID -- run /extract-TI-course or "
                    f"/get-TI-course-structure first to find entity UUIDs."
                )
    return errors


def summarize(course_attributes: dict) -> str:
    parts = []
    for entity_type in ("sections", "lessons", "topics"):
        items = course_attributes.get(entity_type, [])
        if items:
            parts.append(f"{len(items)} {entity_type}")
    return ", ".join(parts) or "(empty)"


# -- API call ------------------------------------------------------------------

def put_update(base_url: str, api_key: str, course_attributes: dict) -> dict:
    url = f"{base_url}/incoming/v2/content/course/update"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.put(
        url, headers=headers,
        json={"courseAttributes": course_attributes},
        timeout=60,
    )
    if resp.status_code not in (200, 201, 204):
        print(f"[ERROR] API returned {resp.status_code}: {resp.text[:400]}")
        resp.raise_for_status()
    return resp.json() if resp.content else {}


# -- Main ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Targeted update of specific topics/lessons/sections in TI"
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--payload", help="Path to JSON file containing the update payload")
    src.add_argument("--json", dest="inline_json", help="Inline JSON payload string")
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate and print the payload without calling the API"
    )
    args = parser.parse_args()

    # -- Load payload ----------------------------------------------------------
    if args.payload:
        p = Path(args.payload)
        if not p.exists():
            print(f"[ERROR] Payload file not found: {p}")
            sys.exit(1)
        data = json.loads(p.read_text(encoding="utf-8"))
    else:
        try:
            data = json.loads(args.inline_json)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON: {e}")
            sys.exit(1)

    # Accept either { "courseAttributes": {...} } or the inner object directly
    if "courseAttributes" in data:
        course_attributes = data["courseAttributes"]
    else:
        course_attributes = data

    # -- Validate --------------------------------------------------------------
    errors = validate_payload(course_attributes)
    if errors:
        print("[ERROR] Payload validation failed:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    summary = summarize(course_attributes)
    print(f"Update payload: {summary}")
    print(json.dumps({"courseAttributes": course_attributes}, indent=2))

    if args.dry_run:
        print("\n[DRY RUN] No changes made. Remove --dry-run to apply.")
        return

    # -- Apply -----------------------------------------------------------------
    creds = resolve_credentials()
    base_url = creds["base_url"].rstrip("/")
    api_key = creds["api_key"]

    print("\nApplying update to TI...")
    result = put_update(base_url, api_key, course_attributes)
    print("Done.")
    if result:
        preview = json.dumps(result, indent=2)
        print(preview[:600] + ("..." if len(preview) > 600 else ""))


if __name__ == "__main__":
    main()
