---
name: "extract-TI-course"
description: "Extract an existing course from Thought Industries and save it as structured .md files organised by section, lesson, and topic for use as reference material."
---

# Extract TI Course

Extract an existing course from the TI LMS. Produces clean `.md` reference files organised by
section/lesson/topic hierarchy. Uses the REST API (bearer-token auth — no API key exposed in URLs).

Uses two co-located scripts: `ti_extract_run.py` (fetch) and `ti_extract_parse.py` (parse).

---

## Step 1 — Ask for inputs

1. **Course identifier** — ask the user to provide one of:
   - **UUID from TI admin URL (preferred)** — open the course in TI admin
     (`/admin/courseGroups/{UUID}/edit`) and copy the UUID from the URL.
     Pass it as `--course-id`; the script automatically resolves it to the
     correct course UUID via `displayCourse` before fetching content.
   - A full Academy URL — extract the slug and run a two-call lookup (see below).
   - A bare slug, e.g. `connect` or `data-integration-basics` — also uses the two-call lookup.

2. **Output folder** — default: `courses/<slug>/01_Source_Material/LMS_Reference/`

### URL → Slug extraction rules

If the user provides a URL, extract the slug before running the lookup:

| URL pattern | Slug extraction |
|---|---|
| `…/courses/<slug>` | Everything after `courses/` (strip trailing slash) |
| `…/learn/course/<slug>/…` | Segment immediately after `course/` (up to next `/`) |
| No URL pattern match | Treat the entire input as a bare slug |

**Examples:**
- `https://academy.celonis.com/courses/process-mining-key-concepts` → `process-mining-key-concepts`
- `https://academy.celonis.com/learn/course/ai-foundations/section-1/lesson-1` → `ai-foundations`

Confirm the extracted slug (or UUID) with the user before proceeding.

---

## Step 2 — Resolve paths

- **Script folder**: set by running `python setup.py` from the plugin root once after installation
- **Output folder**: the confirmed output directory
- **Raw JSON path**: temp file, e.g. `<output_folder>/<slug>_raw.json`

---

## Step 3 — Fetch the course JSON

Using a slug:
```bash
python "$CLAUDE_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_run.py" \
  --slug "<slug>" \
  --output "<raw_json_path>"
```

Using a course UUID (preferred):
```bash
python "$CLAUDE_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_run.py" \
  --course-id "<uuid>" \
  --output "<raw_json_path>"
```

Credentials are resolved automatically via `lib/config.py` (env vars or `secrets.env`).
The API key is sent as a bearer token header — not embedded in any URL.

Fetches `GET /incoming/v2/fullContent/courses/{id}` — returns the complete course tree
including topic body HTML in a single call. No pagination.

When using `--course-id`, the script first calls `courseGroups/{id}/displayCourse` to
resolve the courseGroup UUID (from the admin URL) to the actual course UUID, then calls
fullContent. If that resolution step returns nothing, the UUID is used directly.

When using `--slug`, the same two-call chain runs: `courseGroups/slug/{slug}` →
`courseGroups/{id}/displayCourse` → course UUID, then fullContent.

The output shows how many topics have body HTML — e.g. `(42 topics have body HTML)`. If
that count is 0, the UUID may be wrong or the course may not have text content published
via the Incoming API.

---

## Step 4 — Parse into .md files

```bash
python "$CLAUDE_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_parse.py" \
  "<raw_json_path>" "<output_folder>"
```

No external dependencies required for parsing.

---

## Step 5 — Report results

Show the parser output summary:
- Course title
- Section / lesson / topic counts
- Text-rich topic types found (TextPage, VideoPage, etc.)
- Topics skipped (quiz, test, SCORM, etc.)
- Output location (user-facing workspace path)

### Output structure

```
<output_folder>/<course-slug>/
  _index.md                         ← table of contents (all sections/lessons)
  <section-slug>/
    <lesson-slug>.md                ← one file per lesson
    <lesson-slug>.md
  <section-slug>/
    ...
```

Each lesson file contains:
- YAML frontmatter (`course`, `section`, `lesson`)
- `# Lesson Title` as the H1
- One `## Topic Title` section per topic, with topic body HTML converted to Markdown

Page types and what is extracted:

| Type | What is extracted |
|---|---|
| TextPage, NotebookPage | body + contentDescription / Estimate / Time metadata |
| ArticlePage | body + contentDescription |
| VideoPage | preTextBlock, body, video ID placeholder, postTextBlock |
| AudioPage | preTextBlock, caption, audio placeholder, postTextBlock |
| PDFViewerPage | preTextBlock, PDF placeholder, postTextBlock |
| HtmlEmbedPage | scripts field (HTML converted to Markdown) |
| PresentationPage, SlideshowPage | preTextBlock, each slide (title + caption + alt), postTextBlock |
| FlipCardPage | preTextBlock, each card (title + front + back + alt), postTextBlock |
| ListRollPage | preTextBlock, description, expandable list items, postTextBlock |
| HighlightZonePage | preTextBlock, each zone (title + caption + alt), image alt, postTextBlock |
| InteractivePage | preTextBlock, hotspot captions, postTextBlock |
| AssignmentPage | preTextBlock, description, postTextBlock |
| MatchPairPage | preTextBlock, match pairs (clue -> caption), postTextBlock |
| RecipePage | preTextBlock, description, time/yield, pairing, ingredients, steps |
| TestPage | startMessage, passMessage, failMessage |
| Unknown types | generic fallback extracts preTextBlock, body, description, scripts, postTextBlock |
| QuizPage, SurveyPage, WorkbookPage, ScormPage, MeetingPage, TallyPage, GeneralPage | skipped (no extractable text) |

Typical course: ~5-8 sections, ~20-30 lesson files, compared to ~100 per-topic files in the old structure.
