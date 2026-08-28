---
name: "extract-TI-course"
description: "Extract an existing Thought Industries course or learning path and save it as structured .md files. Accepts a TI admin UUID, an academy.celonis.com course URL, a learning-path URL, or a bare slug. Trigger on: 'pull/extract/download course content', 'get content from academy.celonis.com/…', 'extract this course for reference', 'extract this learning path', 'save this TI course as reference material'."
---

# Extract TI Course or Learning Path

Extract an existing course or learning path from the TI LMS. Produces clean `.md` reference
files. Uses the REST API (bearer-token auth — no API key exposed in URLs).

Uses two co-located scripts: `ti_extract_run.py` (fetch) and `ti_extract_parse.py` (parse).

---

## Step 1 — Ask for inputs

1. **Course or learning path identifier** — ask the user to provide one of:
   - **UUID from TI admin URL (preferred for courses)** — open the course in TI admin
     (`/admin/courseGroups/{UUID}/edit`) and copy the UUID from the URL.
     Pass it as `--course-id`; the script automatically resolves it to the
     correct course UUID via `displayCourse` before fetching content.
   - A full Academy course URL — extract the slug and run a two-call lookup (see below).
   - A bare course slug, e.g. `connect` or `data-integration-basics`.
   - **A full learning path URL** — if the URL contains `/learning-path/`, extract the slug and
     use `--learning-path`. The script resolves it via the List Content endpoint.
   - A bare learning path slug or learning path UUID — pass as `--learning-path`.

2. **Output folder** — default: `courses/<slug>/01_Source_Material/LMS_Reference/`

### URL → Slug extraction rules

| URL pattern | What to extract | Flag to use |
|---|---|---|
| `…/courses/<slug>` | After `courses/` | `--slug` |
| `…/learn/course/<slug>/…` | Segment after `course/` | `--slug` |
| `…/learning-path/<slug>` | After `learning-path/` | `--learning-path` |
| No URL pattern match | Treat as a bare course slug | `--slug` |

**Examples:**
- `https://academy.celonis.com/courses/process-mining-key-concepts` → `--slug process-mining-key-concepts`
- `https://academy.celonis.com/learn/course/ai-foundations/section-1/lesson-1` → `--slug ai-foundations`
- `https://academy.celonis.com/learning-path/data-analyst-foundations` → `--learning-path data-analyst-foundations`

You can also pass a full URL directly to `--learning-path` — the script strips the slug automatically.

Confirm the extracted slug (or UUID) with the user before proceeding.

---

## Step 2 — Resolve paths

- **Script folder**: set by running `python setup.py` from the plugin root once after installation
- **Output folder**: the confirmed output directory
- **Raw JSON path**: temp file, e.g. `<output_folder>/<slug>_raw.json`

---

## Step 3 — Fetch the course or learning path JSON

**Course — using a slug:**
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_run.py" \
  --slug "<slug>" \
  --output "<raw_json_path>"
```

**Course — using a UUID (preferred):**
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_run.py" \
  --course-id "<uuid>" \
  --output "<raw_json_path>"
```

**Learning path — slug, UUID, or full URL:**
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_run.py" \
  --learning-path "<slug_or_uuid_or_full_url>" \
  --output "<raw_json_path>"
```

Credentials are resolved automatically via `lib/config.py` (env vars or `secrets.env`).
The API key is sent as a bearer token header — not embedded in any URL.

**Course fetching:** calls `GET /incoming/v2/fullContent/courses/{id}` — returns the complete
course tree including topic body HTML in a single call. When using `--course-id`, resolves
courseGroup UUID → course UUID via `displayCourse` first. When using `--slug`, uses the two-call
chain `courseGroups/slug/{slug}` → `displayCourse`. The output shows how many topics have body
HTML — if that count is 0, the UUID may be wrong or content may not be published via the API.

**Learning path fetching:** if a slug is given, first calls
`GET /incoming/v2/content?types[]=learningPaths&query=slug:{slug}` to resolve the UUID, then
calls `GET /incoming/v2/fullContent/learningPaths/{id}`. A UUID or a full `/learning-path/` URL
can also be passed directly.

---

## Step 4 — Parse into .md files

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/extract-TI-course/ti_extract_parse.py" \
  "<raw_json_path>" "<output_folder>"
```

No external dependencies required for parsing.

---

## Step 5 — Report results

Show the parser output summary:
- Course title (or learning path name)
- Section / lesson / topic counts (course) OR milestone / course counts (learning path)
- Text-rich topic types found (TextPage, VideoPage, etc.)
- Topics skipped (quiz, test, SCORM, etc.)
- Output location (user-facing workspace path)

### Output structure — course

```
<output_folder>/<course-slug>/
  _index.md                         ← table of contents (all sections/lessons)
  <section-slug>/
    <lesson-slug>.md                ← one file per lesson
    <lesson-slug>.md
  <section-slug>/
    ...
```

### Output structure — learning path

```
<output_folder>/<learning-path-slug>/
  _index.md    ← milestones and course list with UUIDs
```

`_index.md` lists each milestone and its courses as a table. Each row shows the course title
and its UUID. To extract the full content of any course in the path, run
`/extract-TI-course` with `--course-id <uuid>` using the UUID from the table.

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
