#!/usr/bin/env python3
"""
ti_uploader.py
Generic Thought Industries Incoming API v2 uploader.

Usage:
  python ti_uploader.py --payload upload_payload.json --course-id <COURSE_ID>

Payload JSON format:
  {
    "sections": [
      {
        "title": "Section Title",
        "lessons": [
          {
            "title": "Lesson Title",
            "topics": [
              {"title": "Topic Title", "type": "text", "body": "<p>HTML</p>"}
            ]
          }
        ]
      }
    ]
  }

Credentials are resolved via lib/config.py, which checks (in order):
  1. secrets.env in workspace root or any parent folder (up to 5 levels)
  2. secrets.env in the plugin install folder (persists in Cowork)
  3. ~/.claude/secrets.env (desktop only)
  4. Existing environment variables (e.g. set in Claude Code settings.json)
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "--break-system-packages", "-q"])
    import requests

# ---------------------------------------------------------------------------
# Credentials via lib/config.py
# ---------------------------------------------------------------------------

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
from lib.config import resolve_credentials  # noqa: E402


# ---------------------------------------------------------------------------
# API helpers
# ---------------------------------------------------------------------------

def headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def put_update(base_url, api_key, course_attributes: dict):
    url = f"{base_url}/incoming/v2/content/course/update"
    resp = requests.put(url, headers=headers(api_key), json={"courseAttributes": course_attributes}, timeout=60)
    if resp.status_code not in (200, 201, 204):
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    return resp


def _extract_course_id(raw: dict) -> str:
    """Extract course UUID from a TI create response dict. Raises if not found."""
    if raw.get("courseIds") and isinstance(raw["courseIds"], list):
        course_id = str(raw["courseIds"][0])
        group_ids = raw.get("courseGroupIds", [])
        if group_ids:
            print(f"  Course group ID : {group_ids[0]}")
        return course_id
    # Unwrap common single-object envelopes
    for key in ("courseGroup", "course", "data"):
        if key in raw and isinstance(raw[key], dict):
            raw = raw[key]
            break
    course_id = raw.get("id") or raw.get("courseId") or raw.get("uuid")
    if not course_id:
        raise RuntimeError(f"Could not extract course ID from create response: {json.dumps(raw)[:300]}")
    return str(course_id)


def create_course_shell(base_url: str, api_key: str, course_meta: dict) -> str:
    """Create a new course shell (metadata only) via POST /incoming/v2/content/course/create.
    Used for video kind courses and when uploading to an existing shell.
    Returns the new course UUID.
    """
    url = f"{base_url}/incoming/v2/content/course/create"
    resp = requests.post(url, headers=headers(api_key), json={"courseAttributes": [course_meta]}, timeout=60)
    if resp.status_code not in (200, 201):
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    return _extract_course_id(resp.json())


def create_course_with_content(base_url: str, api_key: str, course_meta: dict, payload: dict) -> str:
    """Create a courseGroup with all sections/lessons/topics in a single POST.
    Adds openType='studentsOnly' to each lesson (required by the TI API for nested create).
    Returns the new course UUID.
    """
    nested_sections = []
    for sec in payload.get("sections", []):
        nested_lessons = []
        for les in sec.get("lessons", []):
            lesson = {
                "title": les["title"],
                "openType": les.get("openType", "studentsOnly"),
            }
            topics = []
            for top in les.get("topics", []):
                t = {"title": top["title"], "type": top.get("type", "text")}
                if top.get("body"):
                    t["body"] = top["body"]
                topics.append(t)
            if topics:
                lesson["topics"] = topics
            nested_lessons.append(lesson)
        section = {"title": sec["title"]}
        if nested_lessons:
            section["lessons"] = nested_lessons
        nested_sections.append(section)

    attrs = dict(course_meta)
    if nested_sections:
        attrs["sections"] = nested_sections

    url = f"{base_url}/incoming/v2/content/course/create"
    resp = requests.post(url, headers=headers(api_key), json={"courseAttributes": [attrs]}, timeout=60)
    if resp.status_code not in (200, 201):
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
        resp.raise_for_status()
    return _extract_course_id(resp.json())


def _unwrap_list(raw, key_hint: str = None) -> list:
    """
    TI API responses vary: flat list, or wrapped in a key like
    {"sections": [...]} / {"courseGroup": {"sections": [...]}} / {"data": [...]}.
    Always return a list of dicts.
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        # Unwrap courseGroup envelope first (some TI tenants nest responses here)
        if "courseGroup" in raw and isinstance(raw["courseGroup"], dict):
            raw = raw["courseGroup"]
        # Try the expected key first, then fall back to common wrapper keys
        search_keys = ([key_hint] if key_hint else []) + [
            "sections", "lessons", "topics", "data", "items", "results"
        ]
        for key in search_keys:
            if key and key in raw and isinstance(raw[key], list):
                return raw[key]
        # Single-object response -- wrap it
        return [raw]
    return []


def get_sections(base_url, api_key, course_id: str) -> list:
    url = f"{base_url}/incoming/v2/courses/{course_id}/sections"
    resp = requests.get(url, headers=headers(api_key), timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    result = _unwrap_list(raw, key_hint="sections")
    if not result:
        print(f"  DEBUG get_sections raw response: {json.dumps(raw)[:400]}")
    return result


def get_lessons(base_url, api_key, course_id: str) -> list:
    url = f"{base_url}/incoming/v2/courses/{course_id}/lessons"
    resp = requests.get(url, headers=headers(api_key), timeout=30)
    resp.raise_for_status()
    raw = resp.json()
    result = _unwrap_list(raw, key_hint="lessons")
    if not result:
        print(f"  DEBUG get_lessons raw response: {json.dumps(raw)[:400]}")
    return result


def chunks(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# ---------------------------------------------------------------------------
# Payload pre-processing
# ---------------------------------------------------------------------------

_TIME_RE = re.compile(r"\[\d{1,2}:\d{2}(?::\d{2})?\]|\[\d+\s*mins?\]", re.IGNORECASE)


def strip_time_indicators(payload: dict) -> dict:
    """Remove [01:00], [5 min], [10 mins] markers from topic bodies in place."""
    for sec in payload.get("sections", []):
        for les in sec.get("lessons", []):
            for top in les.get("topics", []):
                if top.get("body"):
                    top["body"] = _TIME_RE.sub("", top["body"]).strip()
    return payload


def find_placeholders(payload: dict) -> list[str]:
    """Return a list of warning strings for unresolved placeholders."""
    warnings = []
    for sec in payload.get("sections", []):
        for les in sec.get("lessons", []):
            for top in les.get("topics", []):
                body = top.get("body", "")
                if "PENDING_CDN_UPLOAD" in body:
                    warnings.append(f"  PENDING_CDN_UPLOAD found in topic '{top.get('title', '?')}'")
                if "WISTIA_MEDIA_ID_HERE" in body:
                    warnings.append(f"  WISTIA_MEDIA_ID_HERE found in topic '{top.get('title', '?')}'")
    return warnings


# ---------------------------------------------------------------------------
# Upload phases
# ---------------------------------------------------------------------------

SECTION_CHUNK = 25
LESSON_CHUNK  = 25
TOPIC_CHUNK   = 5


def phase0_detect(base_url, api_key, course_id: str):
    """Return (is_microcourse, existing_lesson_id_or_None)."""
    secs = get_sections(base_url, api_key, course_id)
    print(f"  Course shell has {len(secs)} section(s)")
    if not secs:
        return False, None
    first = secs[0]
    if not isinstance(first, dict):
        print(f"  WARNING: unexpected section format ({type(first).__name__}), treating as standard course")
        return False, None
    if (
        len(secs) == 1
        and first.get("title", "").strip().lower() == "main"
        and len(first.get("lessons", [])) == 1
    ):
        lesson_id = first["lessons"][0].get("id") or first["lessons"][0].get("lessonId")
        return True, lesson_id
    return False, None


def phase1_create_sections(base_url, api_key, course_id: str, payload: dict) -> dict:
    """Create sections; return {title: id} map."""
    pre_existing = get_sections(base_url, api_key, course_id)
    pre_existing_ids = {s.get("id") or s.get("sectionId") for s in pre_existing if isinstance(s, dict)}
    if pre_existing_ids:
        print(f"  Shell has {len(pre_existing_ids)} pre-existing section(s) — binding to newly created sections only")

    section_defs = [{"courseId": course_id, "title": s["title"]} for s in payload["sections"]]
    print(f"\nPhase 1 -- creating {len(section_defs)} section(s)...")
    for chunk in chunks(section_defs, SECTION_CHUNK):
        put_update(base_url, api_key, {"sections": chunk})
    time.sleep(1.5)

    remote = get_sections(base_url, api_key, course_id)
    seen: dict[str, list] = {}
    for s in remote:
        sid = s.get("id") or s.get("sectionId")
        if sid in pre_existing_ids:
            continue
        t = s.get("title", "")
        seen.setdefault(t, []).append(sid)

    wanted = [s["title"] for s in payload["sections"]]
    id_map = {}
    counters: dict[str, int] = {}
    for title in wanted:
        idx = counters.get(title, 0)
        id_map[title] = seen.get(title, [None])[idx] if seen.get(title) else None
        counters[title] = idx + 1

    print(f"  Mapped {sum(1 for v in id_map.values() if v)} / {len(id_map)} section IDs")
    return id_map


def phase2_create_lessons(base_url, api_key, course_id: str, payload: dict, section_id_map: dict) -> dict:
    """Create lessons; return {(section_id, title): lesson_id} map."""
    pre_existing = get_lessons(base_url, api_key, course_id)
    pre_existing_ids = {les.get("id") or les.get("lessonId") for les in pre_existing if isinstance(les, dict)}
    if pre_existing_ids:
        print(f"  Shell has {len(pre_existing_ids)} pre-existing lesson(s) — binding to newly created lessons only")

    lesson_defs = []
    for sec in payload["sections"]:
        sid = section_id_map.get(sec["title"])
        if not sid:
            print(f"  WARNING: no section ID for '{sec['title']}' -- skipping its lessons")
            continue
        for les in sec["lessons"]:
            lesson_defs.append({"sectionId": sid, "title": les["title"]})

    print(f"\nPhase 2 -- creating {len(lesson_defs)} lesson(s)...")
    for chunk in chunks(lesson_defs, LESSON_CHUNK):
        put_update(base_url, api_key, {"lessons": chunk})
    time.sleep(1.5)

    remote = get_lessons(base_url, api_key, course_id)
    seen: dict[tuple, list] = {}
    for les in remote:
        lid = les.get("id") or les.get("lessonId")
        if lid in pre_existing_ids:
            continue
        key = (les.get("sectionId"), les.get("title", ""))
        seen.setdefault(key, []).append(lid)

    id_map = {}
    counters: dict[tuple, int] = {}
    for ld in lesson_defs:
        key = (ld["sectionId"], ld["title"])
        idx = counters.get(key, 0)
        ids = seen.get(key, [None])
        id_map[key] = ids[idx] if idx < len(ids) else None
        counters[key] = idx + 1

    print(f"  Mapped {sum(1 for v in id_map.values() if v)} / {len(id_map)} lesson IDs")
    return id_map


def phase3_create_topics(base_url, api_key, payload: dict, section_id_map: dict, lesson_id_map: dict):
    """Create topics in chunks of 5."""
    topic_defs = []
    for sec in payload["sections"]:
        sid = section_id_map.get(sec["title"])
        for les in sec["lessons"]:
            key = (sid, les["title"])
            lid = lesson_id_map.get(key)
            if not lid:
                print(f"  WARNING: no lesson ID for '{les['title']}' in '{sec['title']}' -- skipping {len(les['topics'])} topics")
                continue
            for top in les["topics"]:
                topic_defs.append({
                    "lessonId": lid,
                    "title": top["title"],
                    "type": top.get("type", "text"),
                    "body": top.get("body", ""),
                })

    total = len(topic_defs)
    print(f"\nPhase 3 -- creating {total} topic(s) in chunks of {TOPIC_CHUNK}...")
    created = 0
    for i, chunk in enumerate(chunks(topic_defs, TOPIC_CHUNK)):
        put_update(base_url, api_key, {"topics": chunk})
        created += len(chunk)
        print(f"  {created}/{total} topics uploaded", end="\r")
    print(f"  {created}/{total} topics uploaded")
    return created


def microcourse_upload(base_url, api_key, lesson_id: str, payload: dict):
    """Push all topics directly to the single existing lesson."""
    all_topics = []
    for sec in payload["sections"]:
        for les in sec["lessons"]:
            for top in les["topics"]:
                all_topics.append({
                    "lessonId": lesson_id,
                    "title": top["title"],
                    "type": top.get("type", "text"),
                    "body": top.get("body", ""),
                })
    total = len(all_topics)
    print(f"\nMicroCourse mode -- pushing {total} topic(s) to lesson {lesson_id}...")
    created = 0
    for chunk in chunks(all_topics, TOPIC_CHUNK):
        put_update(base_url, api_key, {"topics": chunk})
        created += len(chunk)
        print(f"  {created}/{total} topics uploaded", end="\r")
    print(f"  {created}/{total} topics uploaded")
    return created


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run_upload(payload_path: str, course_id: str = None, dry_run: bool = False, check_pending: bool = False):
    path = Path(payload_path)
    if not path.exists():
        print(f"ERROR: payload file not found: {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        payload = json.load(f)

    # Pull out the optional course metadata block before processing sections
    course_meta = payload.pop("course", None)

    # Validate SKU length before touching the API
    if course_meta:
        sku = course_meta.get("sku", "")
        if sku and len(sku) > 36:
            print(f"ERROR: 'sku' must be ≤ 36 characters (got {len(sku)}: '{sku}').")
            print("       Shorten the SKU and re-run.")
            sys.exit(1)

    # Validate: must have a course_id OR a course metadata block
    if not course_id and not course_meta:
        print("ERROR: --course-id is required unless the payload contains a top-level \"course\" block.")
        print("  Add a \"course\" block to your payload JSON, e.g.:")
        print('    {"course": {"title": "My Course", "sku": "SKU-001", "kind": "courseGroup"}, "sections": [...]}')
        sys.exit(1)

    # Strip time indicators from all topic bodies
    strip_time_indicators(payload)

    n_sections = len(payload.get("sections", []))
    n_lessons  = sum(len(s.get("lessons", [])) for s in payload.get("sections", []))
    n_topics   = sum(
        len(les.get("topics", []))
        for s in payload.get("sections", [])
        for les in s.get("lessons", [])
    )

    placeholders = find_placeholders(payload)

    if dry_run:
        if course_meta and not course_id:
            is_shell_only = course_meta.get("kind") in ("video", "article")
            if not is_shell_only and n_sections > 0:
                print(f"Would create course with all content in one call: \"{course_meta.get('title', '?')}\" "
                      f"(sku: {course_meta.get('sku', '?')}, {n_sections} section(s), {n_lessons} lesson(s), {n_topics} topic(s))")
            else:
                print(f"Would create new course shell: \"{course_meta.get('title', '?')}\" "
                      f"(sku: {course_meta.get('sku', '?')}, kind: {course_meta.get('kind', 'courseGroup')})")
        else:
            print(f"Course ID: {course_id}")
            print(f"Dry run -- {n_sections} section(s), {n_lessons} lesson(s), {n_topics} topic(s)")
        if placeholders:
            print("\nWarnings (unresolved placeholders):")
            for w in placeholders:
                print(w)
        else:
            print("No unresolved placeholders found")
        return

    if check_pending and placeholders:
        print("ERROR: unresolved placeholders found -- upload aborted:")
        for w in placeholders:
            print(w)
        sys.exit(1)

    if placeholders:
        print("WARNING: unresolved placeholders in payload:")
        for w in placeholders:
            print(w)
        print("Proceeding anyway -- use --check-pending to abort on warnings.")

    creds = resolve_credentials()
    base_url = creds["base_url"]
    api_key  = creds["api_key"]
    print(f"  TI_BASE_URL : {base_url}")
    print(f"  TI_API_KEY  : SET ({len(api_key)} chars)")

    # Create course if no course_id was provided
    if not course_id:
        is_shell_only = course_meta.get("kind") in ("video", "article")
        if not is_shell_only and n_sections > 0:
            # courseGroup with content: create everything in one nested POST (bypasses iterative PUT phases)
            print(f"Creating course \"{course_meta.get('title', '?')}\" with "
                  f"{n_sections} section(s), {n_lessons} lesson(s), {n_topics} topic(s)...")
            course_id = create_course_with_content(base_url, api_key, course_meta, payload)
            print(f"  Created course -- ID: {course_id}")
            print(f"\nUpload complete -- {n_topics} topic(s) created.")
            print("\nNext step: run /update-TI-course-metadata to add tags and ribbon.")
            return
        else:
            # Shell-only: video kind or no sections in payload
            print(f"Creating new course shell: \"{course_meta.get('title', '?')}\" ...")
            course_id = create_course_shell(base_url, api_key, course_meta)
            print(f"  Created course shell -- ID: {course_id}")

    if n_sections == 0 and n_lessons == 0:
        print(f"  Course ID: {course_id}")
        print("\nNo sections or lessons in payload -- skipping content upload phases.")
        print("Upload complete -- 0 topic(s) created.")
        print("\nNext step: run /update-TI-course-metadata to add tags and ribbon.")
        return

    print(f"Uploading {n_sections} section(s), {n_lessons} lesson(s), {n_topics} topic(s) to course {course_id}...")

    is_micro, lesson_id = phase0_detect(base_url, api_key, course_id)

    if is_micro:
        print("Detected MicroCourse shell -- skipping section/lesson creation.")
        created = microcourse_upload(base_url, api_key, lesson_id, payload)
    else:
        section_id_map = phase1_create_sections(base_url, api_key, course_id, payload)
        lesson_id_map  = phase2_create_lessons(base_url, api_key, course_id, payload, section_id_map)
        created        = phase3_create_topics(base_url, api_key, payload, section_id_map, lesson_id_map)

    print(f"\nUpload complete -- {created} topic(s) created.")


def main():
    # Legacy interactive mode when called with no arguments
    if len(sys.argv) == 1:
        print("content-creation-plugin -- TI uploader (interactive mode)")
        payload_path = input("Payload JSON path: ").strip()
        cid = input("Course ID (UUID, or leave blank to create from payload): ").strip()
        run_upload(payload_path, course_id=cid or None)
        return

    parser = argparse.ArgumentParser(description="Upload a course payload to Thought Industries")
    parser.add_argument("--payload",       required=True, help="Path to upload_payload.json")
    parser.add_argument("--course-id",     default=None,
                        help="TI course UUID (the shell to populate). "
                             "If omitted, a new shell is created using the 'course' block in the payload JSON.")
    parser.add_argument("--dry-run",       action="store_true", help="Parse inputs and report without calling the API")
    parser.add_argument("--check-pending", action="store_true", help="Abort if PENDING_CDN_UPLOAD or WISTIA_MEDIA_ID_HERE found")
    args = parser.parse_args()

    run_upload(args.payload, course_id=args.course_id, dry_run=args.dry_run, check_pending=args.check_pending)


if __name__ == "__main__":
    main()
