#!/usr/bin/env python3
"""
TI Course Extractor (REST) -- Fetch full course content via TI Incoming API v2.

Usage:
    python ti_extract_run.py --slug <slug> --output <path>
    python ti_extract_run.py --course-id <uuid> --output <path>

Calls GET /incoming/v2/fullContent/courses/{id} which returns the complete
course tree including topic body HTML in one call.

--course-id accepts either:
  - A courseGroup UUID (the UUID shown in the TI admin URL) -- the script
    resolves it automatically to the actual course UUID via /displayCourse
  - A direct course UUID -- used as-is if displayCourse resolution fails

Credentials are resolved via lib/config.py (secrets.env or environment variables).
Output JSON is compatible with ti_extract_parse.py.
"""

import argparse
import json
import sys
from pathlib import Path

# Bootstrap: add plugin root to path for lib imports
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import resolve_credentials

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests",
                           "--break-system-packages", "-q"])
    import requests

# -- Type mapping: REST contentType -> __typename for ti_extract_parse.py -------
_TYPE_MAP = {
    "text": "TextPage",
    "video": "VideoPage",
    "article": "ArticlePage",
    "quiz": "QuizPage",
    "test": "TestPage",
    "survey": "SurveyPage",
    "assignment": "AssignmentPage",
    "workbook": "WorkbookPage",
    "pdf": "PDFViewerPage",
    "pdfreader": "PDFViewerPage",
    "scorm": "ScormPage",
    "meeting": "MeetingPage",
    "matchpair": "MatchPairPage",
    "tally": "TallyPage",
    "audio": "AudioPage",
    "recipe": "RecipePage",
    "notebook": "NotebookPage",
    "general": "GeneralPage",
    "interactive": "InteractivePage",
    "htmlembed": "HtmlEmbedPage",
    "htmlembedpage": "HtmlEmbedPage",
    "highlightzone": "HighlightZonePage",
    "highlightzonepage": "HighlightZonePage",
    "listroll": "ListRollPage",
    "listrollpage": "ListRollPage",
    "flipcard": "FlipCardPage",
    "flipcardpage": "FlipCardPage",
    "presentation": "PresentationPage",
    "slideshow": "SlideshowPage",
}


def type_to_typename(t_type: str) -> str:
    if not t_type:
        return "TextPage"
    key = t_type.lower().replace("_", "").replace("-", "").replace(" ", "")
    if key in _TYPE_MAP:
        return _TYPE_MAP[key]
    return "".join(w.capitalize() for w in t_type.split("_")) + "Page"


# -- API helpers ----------------------------------------------------------------

def _headers(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _get(base_url: str, api_key: str, path: str) -> object:
    resp = requests.get(
        f"{base_url}/incoming/v2/{path}",
        headers=_headers(api_key),
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"[ERROR] GET /incoming/v2/{path} returned {resp.status_code}: {resp.text[:300]}")
        sys.exit(1)
    return resp.json()


def _get_optional(base_url: str, api_key: str, path: str) -> dict | None:
    """Like _get but returns None instead of exiting on non-200."""
    try:
        resp = requests.get(
            f"{base_url}/incoming/v2/{path}",
            headers=_headers(api_key),
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def list_content_first(base_url: str, api_key: str, types_param: str, query: str) -> dict | None:
    """GET /incoming/v2/content?types[]={types_param}&query={query}; return first contentItem or None."""
    resp = requests.get(
        f"{base_url}/incoming/v2/content",
        headers=_headers(api_key),
        params={"types[]": types_param, "query": query},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    items = resp.json().get("contentItems", [])
    return items[0] if items else None


# -- UUID detection ---------------------------------------------------------------

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I
)

# -- Course ID resolution -------------------------------------------------------

def find_by_slug(base_url: str, api_key: str, slug: str):
    """Two-call lookup: courseGroups/slug/{slug} -> displayCourse -> course UUID.
    Returns (cg_id, cg_title, course_id).
    """
    print(f"Looking up courseGroup for slug '{slug}'...")
    cg = _get(base_url, api_key, f"courseGroups/slug/{slug}")
    cg_id = cg.get("id", "")
    cg_title = cg.get("title", slug)
    if not cg_id:
        print(f"[ERROR] courseGroups/slug/{slug} returned no id.")
        print("  Tip: use --course-id <UUID> directly instead of --slug.")
        sys.exit(1)

    print(f"Fetching display course for courseGroup {cg_id}...")
    course = _get(base_url, api_key, f"courseGroups/{cg_id}/displayCourse")
    course_id = course.get("id", "")
    if not course_id:
        print(f"[ERROR] courseGroups/{cg_id}/displayCourse returned no course id.")
        print("  Tip: use --course-id <UUID> directly instead of --slug.")
        sys.exit(1)

    return cg_id, cg_title, course_id


def resolve_course_id(base_url: str, api_key: str, input_id: str):
    """Accept either a courseGroup UUID or a direct course UUID.

    The UUID shown in the TI admin URL (e.g. /admin/courseGroups/{UUID}/edit)
    is a courseGroup UUID. This function tries /displayCourse on it first to get
    the actual course UUID needed for fullContent/courses/{id}. If that fails,
    the input is used directly as a course UUID.

    Returns (cg_id, course_title, course_id).
    """
    print(f"Resolving course ID: {input_id}...")
    data = _get_optional(base_url, api_key, f"courseGroups/{input_id}/displayCourse")
    if data and data.get("id"):
        course_id = data["id"]
        course_title = data.get("title", "")
        print(f"Resolved courseGroup UUID -> course UUID: {course_id} ('{course_title}')")
        return input_id, course_title, course_id

    # Treat input as a direct course UUID
    print(f"Using as direct course UUID (displayCourse lookup returned nothing).")
    return "", "", input_id


# -- Full-content fetch ---------------------------------------------------------

def get_full_content(base_url: str, api_key: str, course_id: str) -> dict:
    """GET /incoming/v2/fullContent/courses/{id}."""
    print(f"Fetching GET /incoming/v2/fullContent/courses/{course_id}...")
    return _get(base_url, api_key, f"fullContent/courses/{course_id}")


# -- Learning path helpers -------------------------------------------------------

def find_learning_path_by_slug(base_url: str, api_key: str, slug: str):
    """Resolve a learning path slug → (path_id, path_name) via /content list endpoint."""
    print(f"Looking up learning path for slug '{slug}'...")
    item = list_content_first(base_url, api_key, "learningPaths", f"slug:{slug}")
    if not item or not item.get("id"):
        print(f"[ERROR] No learning path found for slug '{slug}'.")
        print("  Tip: use --learning-path <UUID> to pass the ID directly instead.")
        sys.exit(1)
    return item["id"], item.get("title") or item.get("name") or slug


def get_full_learning_path_content(base_url: str, api_key: str, path_id: str) -> dict:
    """GET /incoming/v2/fullContent/learningPaths/{id}."""
    print(f"Fetching GET /incoming/v2/fullContent/learningPaths/{path_id}...")
    return _get(base_url, api_key, f"fullContent/learningPaths/{path_id}")


def parse_learning_path_flat(flat: dict) -> dict:
    """Parse fullContent/learningPaths response (flat dot-notation or nested) into milestones list.

    Handles both shapes:
    - Nested: {"milestones": [{name, courses: [...]}, ...]}
    - Flat:   {"milestone.0.name": "...", "milestone.0.milestoneCourses.0.id": "...", ...}
    """
    if isinstance(flat.get("milestones"), list):
        return flat  # already nested

    result = {k: v for k, v in flat.items() if "." not in k}
    ms: dict = {}

    for raw_key, value in flat.items():
        parts = raw_key.split(".")
        if parts[0] != "milestone" or len(parts) < 3:
            continue
        try:
            i = int(parts[1])
        except ValueError:
            continue
        ms.setdefault(i, {"courses": {}})
        if len(parts) == 3:
            ms[i][parts[2]] = value
        elif len(parts) == 5 and parts[2] == "milestoneCourses":
            try:
                j = int(parts[3])
            except ValueError:
                continue
            ms[i]["courses"].setdefault(j, {})
            ms[i]["courses"][j][parts[4]] = value

    milestones = []
    for i in sorted(ms):
        courses = [ms[i]["courses"][j] for j in sorted(ms[i].get("courses", {}))]
        milestones.append({"name": ms[i].get("name", ""), "courses": courses})

    result["milestones"] = milestones
    return result


def extract_learning_path(base_url: str, api_key: str, lp_input: str, lp_name: str = "") -> dict:
    """Fetch and parse a learning path. lp_input may be a UUID, slug, or full URL."""
    if _UUID_RE.match(lp_input):
        path_id = lp_input
        if not lp_name:
            lp_name = path_id
    else:
        path_id, lp_name = find_learning_path_by_slug(base_url, api_key, lp_input)
        print(f"Found: '{lp_name}' (UUID: {path_id})")

    flat = get_full_learning_path_content(base_url, api_key, path_id)
    lp = parse_learning_path_flat(flat)

    if not lp_name or lp_name == path_id:
        lp_name = lp.get("name") or lp.get("title") or path_id

    n_milestones = len(lp.get("milestones", []))
    n_courses = sum(len(m.get("courses", [])) for m in lp.get("milestones", []))
    print(f"Extracted: {n_milestones} milestone(s), {n_courses} course(s)")

    return {
        "data": {
            "LearningPath": {
                "id": path_id,
                "name": lp_name,
                "shortDescription": lp.get("shortDescription", ""),
                "milestones": lp.get("milestones", []),
            }
        }
    }


# -- Flat dot-notation parser ---------------------------------------------------

def _set_nested_path(obj, keys, value):
    """Recursively set a value at an alternating string/integer key path.

    String keys → dict fields. Numeric-string keys → list indices (list created if absent).
    Example: keys=['expandableLists','0','expandableListItems','0','title'] value='Foo'
    sets obj['expandableLists'][0]['expandableListItems'][0]['title'] = 'Foo'
    """
    if len(keys) == 1:
        obj[keys[0]] = value
        return
    k = keys[0]
    rest = keys[1:]
    if rest[0].isdigit():
        idx = int(rest[0])
        if k not in obj:
            obj[k] = []
        lst = obj[k]
        while len(lst) <= idx:
            lst.append({})
        _set_nested_path(lst[idx], rest[1:], value)
    else:
        if k not in obj:
            obj[k] = {}
        _set_nested_path(obj[k], rest, value)


def parse_flat_response(flat: dict) -> list:
    """Convert TI fullContent response to a nested sections list.

    Handles two response shapes:
    1. Flat dot-notation (TI default):
         { "section.0.id": "...", "section.0.lesson.0.topic.0.body": "..." }
    2. Nested JSON fallback (some API configurations):
         { "sections": [{ "id": "...", "lessons": [...] }] }
    """
    # Nested JSON fallback
    if "sections" in flat and isinstance(flat["sections"], list):
        return flat["sections"]

    sections: dict[int, dict] = {}

    for raw_key, value in flat.items():
        parts = raw_key.split(".")
        try:
            if len(parts) == 3 and parts[0] == "section":
                # section.{i}.{field}
                i = int(parts[1])
                sections.setdefault(i, {"lessons": {}})
                sections[i][parts[2]] = value

            elif len(parts) == 5 and parts[0] == "section" and parts[2] == "lesson":
                # section.{i}.lesson.{j}.{field}
                i, j = int(parts[1]), int(parts[3])
                sections.setdefault(i, {"lessons": {}})
                sections[i]["lessons"].setdefault(j, {"topics": {}})
                sections[i]["lessons"][j][parts[4]] = value

            elif (len(parts) >= 7 and parts[0] == "section"
                  and parts[2] == "lesson" and parts[4] == "topic"):
                # section.{i}.lesson.{j}.topic.{k}.{field}[.{sub-array paths}...]
                i, j, k = int(parts[1]), int(parts[3]), int(parts[5])
                sections.setdefault(i, {"lessons": {}})
                sections[i]["lessons"].setdefault(j, {"topics": {}})
                sections[i]["lessons"][j]["topics"].setdefault(k, {})
                topic = sections[i]["lessons"][j]["topics"][k]
                if len(parts) == 7:
                    topic[parts[6]] = value
                else:
                    # Sub-array fields: expandableLists.0.title, slides.0.caption, etc.
                    _set_nested_path(topic, parts[6:], value)

        except (ValueError, IndexError):
            continue

    if not sections:
        return []

    # Convert integer-keyed dicts to sorted lists
    result = []
    for i in sorted(sections):
        sec = {k: v for k, v in sections[i].items() if k != "lessons"}
        lessons_dict = sections[i].get("lessons", {})
        sec["lessons"] = []
        for j in sorted(lessons_dict):
            les = {k: v for k, v in lessons_dict[j].items() if k != "topics"}
            topics_dict = lessons_dict[j].get("topics", {})
            les["topics"] = [topics_dict[k] for k in sorted(topics_dict)]
            sec["lessons"].append(les)
        result.append(sec)
    return result


# -- Build output ---------------------------------------------------------------

def extract_and_enrich(base_url, api_key, course_id, course_title, cg_id):
    """Fetch fullContent, return JSON envelope compatible with ti_extract_parse.py."""
    flat = get_full_content(base_url, api_key, course_id)

    if not course_title or course_title == course_id:
        course_title = flat.get("title", course_id)

    raw_sections = parse_flat_response(flat)

    if not raw_sections:
        print("[WARN] No sections found in the API response.")
        print("       Possible causes:")
        print("       - The UUID passed is not a valid course or courseGroup UUID.")
        print("       - The course has no sections published via the Incoming API.")
        print("       - The API returned an unexpected format.")
        print(f"       Response keys: {list(flat.keys())[:15]}")

    sections_out = []
    total_lessons = 0
    total_topics = 0
    topics_with_body = 0

    for sec in raw_sections:
        lessons_out = []
        for les in sec.get("lessons", []):
            les_id = les.get("id", "")
            topics_out = []
            for top in les.get("topics", []):
                t_type = top.get("type") or top.get("contentType", "")
                # Try multiple possible body field names
                body = (top.get("body") or top.get("bodyHtml") or
                        top.get("content") or top.get("bodyContent") or "")
                # Preserve ALL raw fields so page handlers (ListRollPage, FlipCardPage, etc.)
                # receive sub-arrays (expandableLists, slides, flipCards, …).
                topic_entry = {
                    **top,
                    "__typename": type_to_typename(t_type),
                    "type": t_type,
                    "body": body,
                    "lessonId": les_id,
                }
                topics_out.append(topic_entry)
                total_topics += 1
                if body:
                    topics_with_body += 1

            lessons_out.append({
                "id": les_id,
                "title": les.get("title", ""),
                "topics": topics_out,
            })
            total_lessons += 1

        sections_out.append({
            "id": sec.get("id", ""),
            "title": sec.get("title", ""),
            "status": sec.get("status", ""),
            "lessons": lessons_out,
        })

    print(
        f"Extracted: {len(sections_out)} sections, "
        f"{total_lessons} lessons, {total_topics} topics "
        f"({topics_with_body} topics have body HTML)"
    )
    if total_topics > 0 and topics_with_body == 0:
        print("[WARN] No topic body content found. The fullContent endpoint may not be")
        print("       returning body for this course, or the topic type may not include body.")

    # Output envelope for ti_extract_parse.py compatibility
    return {
        "data": {
            "CourseGroupBySlug": {
                "id": cg_id or course_id,
                "title": course_title,
                "courses": [{"id": course_id, "sections": sections_out}],
            }
        }
    }


# -- Main -----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Extract a TI course or learning path via REST API.\n"
            "Uses GET /incoming/v2/fullContent/courses/{id} or fullContent/learningPaths/{id}.\n"
            "Bearer-token auth -- API key is never exposed in URLs."
        )
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument(
        "--slug",
        help="Course slug (e.g. 'data-integration-basics')"
    )
    src.add_argument(
        "--course-id",
        help=(
            "Course or courseGroup UUID. Pass the UUID from the TI admin URL "
            "(e.g. /admin/courseGroups/{UUID}/edit) -- the script resolves it automatically."
        )
    )
    src.add_argument(
        "--learning-path",
        help=(
            "Learning path slug, UUID, or full academy.celonis.com/learning-path/… URL. "
            "Slug inputs are resolved to a UUID via the /content list endpoint."
        )
    )
    parser.add_argument("--output", required=True, help="Output path for raw JSON file")
    args = parser.parse_args()

    creds = resolve_credentials()
    base_url = creds["base_url"].rstrip("/")
    api_key = creds["api_key"]

    if args.learning_path:
        lp_input = args.learning_path.strip()
        # Extract slug from a full URL containing /learning-path/
        url_match = re.search(r"/learning-path/([^/?#]+)", lp_input)
        if url_match:
            lp_input = url_match.group(1)
        result = extract_learning_path(base_url, api_key, lp_input)
    else:
        cg_id = ""
        course_title = ""
        if args.slug:
            cg_id, course_title, course_id = find_by_slug(base_url, api_key, args.slug)
            print(f"Found: '{course_title}' (course UUID: {course_id})")
        else:
            cg_id, course_title, course_id = resolve_course_id(
                base_url, api_key, args.course_id.strip()
            )
        result = extract_and_enrich(base_url, api_key, course_id, course_title, cg_id)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Done. Raw JSON saved to: {out_path}")


if __name__ == "__main__":
    main()
