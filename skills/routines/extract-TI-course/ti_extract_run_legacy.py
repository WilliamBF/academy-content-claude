#!/usr/bin/env python3
"""
TI Course Extractor -- Fetch raw course JSON from the TI GraphQL API.

Usage:
    python ti_extract_run.py <slug> <output_path>

Credentials are resolved via lib/config.py:
  Reads from environment variables (set by setup scripts)
"""

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

# -- Args ----------------------------------------------------------------------
if len(sys.argv) != 3:
    print("Usage: python ti_extract_run.py <slug> <output_path>")
    sys.exit(1)

SLUG = sys.argv[1].strip()
OUTPUT_PATH = Path(sys.argv[2])

# -- Resolve credentials -------------------------------------------------------
creds = resolve_credentials()
TI_BASE_URL = creds["base_url"]
API_KEY = creds["api_key"]

# -- GraphQL query -------------------------------------------------------------
QUERY = """
query CourseGroupBySlug($slug: Slug!) {
  CourseGroupBySlug(slug: $slug) {
    id
    title
    courses {
      id
      sections {
        status
        title
        lessons {
          title
          topics {
            __typename
            ...on TextPage {
              title body type id
            }
            ...on HighlightZonePage {
              title preTextBlock postTextBlock
              highlightZones { title caption altText }
            }
            ...on ListRollPage {
              title preTextBlock postTextBlock
              expandableLists {
                title
                expandableListItems { title description }
              }
            }
            ...on FlipCardPage {
              title preTextBlock postTextBlock
              flipCards { title frontText description altText }
            }
            ...on PresentationPage {
              title preTextBlock postTextBlock
              slides { title caption altText asset audioAsset }
            }
            ...on SlideshowPage {
              title preTextBlock postTextBlock
              slides { title caption altText asset audioAsset }
            }
            ...on VideoPage {
              title preTextBlock body id lessonId type
            }
            ...on ArticlePage {
              title type id videoAsset contentDescription
            }
            ...on HtmlEmbedPage   { title type id scripts }
            ...on QuizPage        { title type }
            ...on TestPage        { title type }
            ...on SurveyPage      { title type }
            ...on AssignmentPage  { title type }
            ...on WorkbookPage    { title }
            ...on PDFViewerPage   { title type }
            ...on ScormPage       { title }
            ...on MeetingPage     { title type }
            ...on MatchPairPage   { title type }
            ...on TallyPage       { title type }
            ...on AudioPage       { title }
            ...on RecipePage      { title }
            ...on NotebookPage    { title }
            ...on GeneralPage     { title type }
            ...on InteractivePage { title }
          }
        }
      }
    }
  }
}
"""

# -- Run -----------------------------------------------------------------------
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}",
}

print(f"Querying course: {SLUG}")
resp = requests.post(
    f"{TI_BASE_URL}/helium?apiKey={API_KEY}",
    json={"query": QUERY, "variables": {"slug": SLUG}},
    headers=headers,
    timeout=30,
)

if resp.status_code != 200:
    print(f"[ERROR] API returned {resp.status_code}: {resp.text}")
    sys.exit(1)

data = resp.json()
if "errors" in data:
    print(f"[ERROR] GraphQL errors: {json.dumps(data['errors'], indent=2)}")
    sys.exit(1)

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
print(f"Done. Raw JSON saved to: {OUTPUT_PATH}")
