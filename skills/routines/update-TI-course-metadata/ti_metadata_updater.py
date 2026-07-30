#!/usr/bin/env python3
"""
ti_metadata_updater.py - Update course-group-level metadata on an existing TI course shell.

Usage:
    # Show current metadata for a course (accepts either Course UUID or Course Group ID)
    python ti_metadata_updater.py --course-id <UUID> --show-current

    # Dry run (prints the exact PUT body, does not write)
    python ti_metadata_updater.py --course-id <UUID> --payload metadata.json --dry-run

    # Apply
    python ti_metadata_updater.py --course-id <UUID> --payload metadata.json

    # Or pass the payload inline
    python ti_metadata_updater.py --course-id <UUID> --json '{"description": "..."}'

Payload JSON format (human-name inputs):
    {
      "description": "...",           # <=100 chars (house rule), API allows 5000
      "metaTitle": "...",             # "<Course Title> | Celonis Academy"
      "metaDescription": "...",       # <=155 chars per Confluence guidelines
      "customFields": {
        "duration": "1 h - 1 h 30",   # single-select
        "level": "Intermediate",      # single-select
        "product": ["AI"],            # multi-select; UI label = "Feature"
        "role": ["Data Analyst"]      # multi-select
      },
      "tags": ["academy", "Owner Nicole Wendler"],  # human names; script -> UUIDs
      "ribbon": "New!"                              # display or slug; script -> slug
    }

The script wraps the final payload as:
    {"courseAttributes": {"courseGroups": [{"id": <groupId>, ...validated}]}}
    PUT /incoming/v2/content/course/update

Credentials come from secrets.env via lib/config.py.

Notes:
- `source` field is not writable via this endpoint. Skill instructs LXD to set manually.
- `tagIds` is not returned by the GET endpoint; skill relies on write success + UI verification.
- Any unknown key in the payload is passed through as-is (LXD's responsibility if used).
"""

import argparse
import json
import sys
from pathlib import Path

# Bootstrap: add plugin root to path for lib imports
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import resolve_credentials  # noqa: E402

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests",
                           "--break-system-packages", "-q"])
    import requests


HERE = Path(__file__).resolve().parent
TAXONOMY_PATH = HERE / "ti_taxonomy.json"

# Fields the API accepts as top-level on a courseGroup update
KNOWN_TOP_LEVEL_FIELDS = {
    "id", "title", "slug", "description", "tagIds", "customFields",
    "asset", "assetAltText", "detailAsset", "detailAssetAltText",
    "ribbon", "metaTitle", "metaDescription",
}
VISIBILITY_TAGS = {"internal", "public", "customer", "partner", "academic"}
SAFE_AUDIENCE_TAG = "academy"
HOUSE_DESCRIPTION_MAX = 100
HOUSE_META_DESCRIPTION_MAX = 155


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_taxonomy() -> dict:
    if not TAXONOMY_PATH.exists():
        print(f"[ERROR] Taxonomy file missing: {TAXONOMY_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(TAXONOMY_PATH.read_text(encoding="utf-8"))


def api_headers(api_key: str, content_type: bool = False) -> dict:
    h = {"Authorization": f"Bearer {api_key}"}
    if content_type:
        h["Content-Type"] = "application/json"
    return h


def resolve_group_id(base_url: str, api_key: str, given_id: str) -> str:
    """
    Accept either a Course Group ID or a Course UUID and return the Course Group ID.
    Strategy:
      1. Try GET /incoming/v2/courseGroups/<given_id>. If HTTP 200 with a body that has 'id',
         it's already a Group ID.
      2. Otherwise, paginate /incoming/v2/courseGroups looking for displayCourseId == given_id.
    """
    r = requests.get(f"{base_url}/incoming/v2/courseGroups/{given_id}",
                     headers=api_headers(api_key), timeout=30)
    if r.status_code == 200:
        body = r.json()
        # TI returns 200 even when the group isn't found (with an 'errors' array in body).
        if isinstance(body, dict) and body.get("id") == given_id:
            return given_id

    # Fall back: scan the catalog for a matching displayCourseId
    print(f"[info] '{given_id}' is not a Course Group ID directly; scanning catalog for match...",
          file=sys.stderr)
    cursor = None
    for _ in range(200):  # safety bound on pagination
        params = {"per_page": 50}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{base_url}/incoming/v2/courseGroups",
                         headers=api_headers(api_key), params=params, timeout=30)
        if r.status_code != 200:
            print(f"[ERROR] Catalog listing failed: HTTP {r.status_code}: {r.text[:200]}",
                  file=sys.stderr)
            sys.exit(1)
        body = r.json()
        for cg in body.get("courseGroups", []):
            if cg.get("displayCourseId") == given_id:
                gid = cg.get("id")
                print(f"[info] Resolved Course UUID {given_id} -> Course Group ID {gid}",
                      file=sys.stderr)
                return gid
        pi = body.get("pageInfo", {})
        if not pi.get("hasMore"):
            break
        cursor = pi.get("cursor")

    print(f"[ERROR] Could not resolve '{given_id}' to a Course Group ID. If the course shell is "
          f"unpublished it may not appear in the catalog listing - ask the LXD for the Course "
          f"Group ID directly (visible in the TI admin URL).", file=sys.stderr)
    sys.exit(1)


def fetch_course_group(base_url: str, api_key: str, group_id: str) -> dict:
    r = requests.get(f"{base_url}/incoming/v2/courseGroups/{group_id}",
                     headers=api_headers(api_key), timeout=30)
    if r.status_code != 200:
        print(f"[ERROR] GET /courseGroups/{group_id} -> HTTP {r.status_code}: {r.text[:200]}",
              file=sys.stderr)
        sys.exit(1)
    return r.json()


# ---------------------------------------------------------------------------
# Validation / translation
# ---------------------------------------------------------------------------

def translate_tags(tag_names: list, taxonomy: dict, warnings: list, force_visibility: bool) -> list:
    """Translate human tag names to UUIDs. Warn (or fail) on visibility-changing tags."""
    audience = taxonomy.get("audience_tags", {})
    owners = taxonomy.get("owner_tags", {})
    lookup = {**{k: v for k, v in audience.items() if not k.startswith("_")},
              **{k: v for k, v in owners.items() if not k.startswith("_")}}

    tag_ids = []
    for name in tag_names:
        if name in lookup:
            uuid = lookup[name]
            if name in VISIBILITY_TAGS and not force_visibility:
                warnings.append(
                    f"AUDIENCE TAG '{name}' will make the course visible to everyone tagged "
                    f"'{name}' in Academy. Confirm with the LXD before applying. Re-run with "
                    f"--force-visibility-tags once explicitly confirmed."
                )
            tag_ids.append(uuid)
        else:
            # Assume it's already a UUID
            if len(name) == 36 and name.count("-") == 4:
                warnings.append(f"tag '{name}' looks like a UUID; passing through unchanged.")
                tag_ids.append(name)
            else:
                print(f"[ERROR] Unknown tag name '{name}'. Not in ti_taxonomy.json. "
                      f"Update the taxonomy or pass the UUID directly.", file=sys.stderr)
                sys.exit(1)
    return tag_ids


def translate_ribbon(ribbon: str, taxonomy: dict) -> str:
    """Accept slug or display name; return the slug."""
    if ribbon is None:
        return None
    slugs = taxonomy.get("ribbon_slugs", {})
    # Direct slug hit
    if ribbon in slugs and not ribbon.startswith("_"):
        return ribbon
    # Display-name lookup (case-insensitive)
    for slug, info in slugs.items():
        if slug.startswith("_"):
            continue
        if ribbon.strip().lower() == info.get("display", "").strip().lower():
            return slug
        if ribbon.strip().lower() == slug:
            return slug
    # Fallback: pass through and let the API tell us it's invalid (helpful error message)
    return ribbon


def validate_custom_fields(cf: dict, taxonomy: dict, warnings: list) -> dict:
    """Translate UI-label keys to API keys, validate option values against enums."""
    field_defs = taxonomy.get("custom_fields", {})
    # Build UI-label -> api_key map (and also allow direct api_key input)
    key_map = {}
    enum_map = {}
    select_map = {}
    for _entry_key, defn in field_defs.items():
        if _entry_key.startswith("_"):
            continue
        api_key = defn["api_key"]
        ui_label = defn["ui_label"]
        key_map[ui_label] = api_key
        key_map[api_key] = api_key
        key_map[_entry_key] = api_key
        enum_map[api_key] = defn["options"]
        select_map[api_key] = defn["select"]

    out = {}
    for k, v in cf.items():
        api_key = key_map.get(k, k)
        if api_key not in enum_map:
            warnings.append(f"custom field '{k}' has no known enum; passing through as-is.")
            out[api_key] = v
            continue
        options = enum_map[api_key]
        if select_map[api_key] == "multi":
            if not isinstance(v, list):
                v = [v]
            for item in v:
                if item not in options:
                    warnings.append(f"'{item}' is not a known option for '{api_key}'. "
                                    f"Valid options: {options}")
            out[api_key] = v
        else:
            if isinstance(v, list):
                warnings.append(f"'{api_key}' is single-select but received a list; using first "
                                f"value '{v[0] if v else None}'")
                v = v[0] if v else None
            if v is not None and v not in options:
                warnings.append(f"'{v}' is not a known option for '{api_key}'. "
                                f"Valid options: {options}")
            out[api_key] = v
    return out


def build_payload(user_payload: dict, taxonomy: dict, force_visibility: bool) -> tuple:
    """Return (validated_fields_dict, warnings_list)."""
    warnings = []
    fields = {}

    for k, v in user_payload.items():
        if k == "description":
            if v is not None and len(v) > HOUSE_DESCRIPTION_MAX:
                warnings.append(f"description is {len(v)} chars; house rule is "
                                f"{HOUSE_DESCRIPTION_MAX}. Trim before writing.")
            fields["description"] = v

        elif k == "metaDescription":
            if v is not None and len(v) > HOUSE_META_DESCRIPTION_MAX:
                warnings.append(f"metaDescription is {len(v)} chars; Confluence guidance is "
                                f"{HOUSE_META_DESCRIPTION_MAX}. Trim before writing.")
            fields["metaDescription"] = v

        elif k == "metaTitle":
            if v is not None and not v.endswith("| Celonis Academy"):
                warnings.append(f"metaTitle does not end with '| Celonis Academy'. "
                                f"House template is '<Course Title> | Celonis Academy'.")
            fields["metaTitle"] = v

        elif k == "customFields":
            fields["customFields"] = validate_custom_fields(v or {}, taxonomy, warnings)

        elif k == "tags":
            fields["tagIds"] = translate_tags(v or [], taxonomy, warnings, force_visibility)

        elif k == "tagIds":
            # Pass UUIDs through unchanged
            fields["tagIds"] = v

        elif k == "ribbon":
            fields["ribbon"] = translate_ribbon(v, taxonomy)

        elif k in KNOWN_TOP_LEVEL_FIELDS:
            fields[k] = v

        else:
            warnings.append(f"Unknown payload key '{k}' - passing through unchanged. "
                            f"Verify it's a valid TI courseGroup field.")
            fields[k] = v

    return fields, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def cmd_show_current(base_url: str, api_key: str, group_id: str):
    cg = fetch_course_group(base_url, api_key, group_id)
    print(json.dumps(cg, indent=2, ensure_ascii=False))
    print("\n(Note: tagIds is not returned by this endpoint even when tags are set. "
          "Verify tags in the TI admin UI.)")


def cmd_update(base_url: str, api_key: str, group_id: str,
               user_payload: dict, dry_run: bool, force_visibility: bool):
    taxonomy = load_taxonomy()
    fields, warnings = build_payload(user_payload, taxonomy, force_visibility)

    # Refuse to write a source field
    if "source" in fields:
        print("[WARN] 'source' cannot be written via this endpoint. Removed from payload. "
              "Set it manually in TI admin UI (Advanced Settings > Source).")
        fields.pop("source", None)

    body = {"courseAttributes": {"courseGroups": [{"id": group_id, **fields}]}}

    print("=== Payload to PUT ===")
    print(json.dumps(body, indent=2, ensure_ascii=False))
    print()

    if warnings:
        print("=== Warnings ===")
        for w in warnings:
            print(f"  - {w}")
        print()

    blocking = [w for w in warnings if w.startswith("AUDIENCE TAG")]
    if blocking and not force_visibility:
        print("[BLOCKED] Audience tag write requires explicit --force-visibility-tags flag. "
              "Confirm with LXD before re-running.", file=sys.stderr)
        sys.exit(2)

    if dry_run:
        print("[dry-run] Not sending PUT. Re-run without --dry-run to apply.")
        return

    r = requests.put(f"{base_url}/incoming/v2/content/course/update",
                     headers=api_headers(api_key, content_type=True),
                     json=body, timeout=30)
    if r.status_code != 200:
        print(f"[ERROR] PUT returned HTTP {r.status_code}: {r.text[:400]}", file=sys.stderr)
        sys.exit(1)

    print(f"[ok] PUT succeeded (HTTP {r.status_code}).")
    print("\n=== Verification (GET /courseGroups/{id}) ===")
    after = fetch_course_group(base_url, api_key, group_id)

    print("Field   | Requested        | Now in TI")
    print("-" * 70)
    for k in ("description", "metaTitle", "metaDescription", "ribbon"):
        if k in fields:
            got = after.get(k)
            match = "OK" if got == fields[k] else "MISMATCH"
            print(f"[{match}] {k}: {fields[k]!r} -> {got!r}")
    if "customFields" in fields:
        got = after.get("customFields", {})
        match = "OK" if got == fields["customFields"] else "MISMATCH"
        print(f"[{match}] customFields: requested={fields['customFields']} got={got}")
    if "tagIds" in fields:
        print(f"[?] tagIds: {len(fields['tagIds'])} tag(s) sent; GET endpoint does not return "
              f"tagIds so please verify visually in TI admin UI.")

    print("\n=== Manual follow-ups ===")
    print("  - Set 'source' (Advanced Settings) manually in TI admin UI - API can't write it.")
    print("  - Add 'Learning Objectives' detail-page tab manually if needed.")
    print("  - Verify tags applied visually in TI admin UI.")


def main():
    parser = argparse.ArgumentParser(description="Update TI course-group metadata")
    parser.add_argument("--course-id", required=True,
                        help="Course Group ID or Course UUID (script resolves either)")
    parser.add_argument("--payload", help="Path to JSON file with metadata fields")
    parser.add_argument("--json", dest="json_inline",
                        help="Inline JSON payload string (alternative to --payload)")
    parser.add_argument("--show-current", action="store_true",
                        help="Print current metadata for the course and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Assemble and print the PUT body but do not send it")
    parser.add_argument("--force-visibility-tags", action="store_true",
                        help="Required to write any audience tag other than 'academy'. "
                             "Confirm with the LXD before using.")
    args = parser.parse_args()

    creds = resolve_credentials()
    base_url = creds["base_url"].rstrip("/")
    api_key = creds["api_key"]

    group_id = resolve_group_id(base_url, api_key, args.course_id)

    if args.show_current:
        cmd_show_current(base_url, api_key, group_id)
        return

    if args.payload:
        user_payload = json.loads(Path(args.payload).read_text(encoding="utf-8"))
    elif args.json_inline:
        user_payload = json.loads(args.json_inline)
    else:
        print("[ERROR] Provide --payload <file> or --json '<inline>' (or --show-current).",
              file=sys.stderr)
        sys.exit(1)

    cmd_update(base_url, api_key, group_id, user_payload,
               dry_run=args.dry_run,
               force_visibility=args.force_visibility_tags)


if __name__ == "__main__":
    main()
