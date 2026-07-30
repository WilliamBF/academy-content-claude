#!/usr/bin/env python3
"""
ti_structure.py -- Fetch and display a TI course's full section/lesson/topic tree.

Usage:
    python ti_structure.py --course-id <UUID>
    python ti_structure.py --course-id <UUID> --output structure.json
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


def main():
    parser = argparse.ArgumentParser(description="Fetch TI course structure (section/lesson/topic tree)")
    parser.add_argument("--course-id", required=True, help="Course UUID")
    parser.add_argument("--output", help="Optional path to save raw JSON")
    args = parser.parse_args()

    creds = resolve_credentials()
    base_url = creds["base_url"].rstrip("/")
    api_key = creds["api_key"]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    resp = requests.get(
        f"{base_url}/incoming/v2/courses/{args.course_id}/structure",
        headers=headers,
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"[ERROR] {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)

    data = resp.json()

    # -- Print tree ------------------------------------------------------------
    course_title = data.get("title", args.course_id)
    sections = data.get("sections", [])

    print(f"Course: {course_title}")
    print(f"Sections: {len(sections)}\n")

    total_lessons = 0
    total_topics = 0

    for sec in sections:
        lessons = sec.get("lessons", [])
        print(f"SECTION  [{sec.get('id', '')}]  {sec.get('title', '')}  ({len(lessons)} lessons)")
        for les in lessons:
            topics = les.get("topics", [])
            print(f"  LESSON [{les.get('id', '')}]  {les.get('title', '')}  ({len(topics)} topics)")
            for top in topics:
                t_type = top.get("type") or top.get("contentType", "")
                print(f"    TOPIC  [{top.get('id', '')}]  {top.get('title', '')}  type={t_type}")
                total_topics += 1
            total_lessons += 1
        print()

    print(f"Total: {len(sections)} sections, {total_lessons} lessons, {total_topics} topics")

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(f"\nStructure JSON saved to: {args.output}")


if __name__ == "__main__":
    main()
