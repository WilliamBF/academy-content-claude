---
name: "upload-course-to-TI"
description: "Upload a course payload JSON to Thought Industries via the Incoming API — creates sections, lessons, and topics in the correct order."
---

# Upload Course to TI

Upload a standardised payload JSON to Thought Industries. Runs after `convert-course-to-html` has generated an `upload_payload.json` and the HTML output in `03_HTML/`.

**Co-located script:** `ti_uploader.py` (same folder as this SKILL.md) — the generic uploader. It never has a course ID baked in; the course ID is always supplied at runtime.

---

## Pre-flight checklist (MUST pass before uploading)

1. **Images resolved** — Scan the payload / HTML for `PENDING_CDN_UPLOAD`. If ANY are found:

   > **Cowork users:** `image_uploader.py` uses Playwright and **cannot run in Cowork**.
   > Switch to Claude Code desktop/CLI (macOS or Windows) for this step, then return to Cowork for the upload itself.

   - Run `image_uploader.py` (in the `course-to-html` skill folder) to upload images to TI CDN:
     ```bash
     python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/image_uploader.py" <images_folder> --output cdn_map.json
     ```
   - Then run `patch_cdn_urls.py` to replace placeholders with real CDN URLs:
     ```bash
     python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/patch_cdn_urls.py" <html_file> cdn_map.json
     ```
   - Only proceed once zero `PENDING_CDN_UPLOAD` strings remain

2. **Videos resolved** — Scan for `WISTIA_MEDIA_ID_HERE`. Replace each with the real Wistia media ID before uploading.

3. **Payload exists** — Confirm `upload_payload.json` (or a named equivalent) is present in `05_LMS_Sync/` for the course.

4. **Course ID** — Either:
   - Have the UUID of an existing shell ready to pass via `--course-id`, **OR**
   - Add a `"course"` block to your `upload_payload.json` (see Payload JSON format below) — the script creates the shell automatically and prints the new course ID.

---

## Step 1 — Gather inputs

You need:
- **Path to the payload JSON** — standardised `upload_payload.json` produced by any convert script
- **Thought Industries Course ID** — one of:
  - The UUID of an existing shell (pass via `--course-id`), **OR**
  - A `"course"` metadata block in the payload (omit `--course-id` and the script creates the shell first, then prints the new UUID)

---

## Step 2 — Resolve credentials

Credentials come from environment variables (typically loaded from `secrets.env`):
- `TI_BASE_URL` — e.g. `https://academy.celonis.com`
- `TI_API_KEY` — Bearer token for the Incoming API

`ti_uploader.py` resolves credentials automatically by calling `lib/config.py → resolve_credentials()`, then falling back to walking up the directory tree for a `secrets.env` or `.env` file. Never print credential values.

---

## Step 3 — Run a dry run first

Always validate before uploading to production:

```bash
# With existing shell:
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py" \
  --payload 05_LMS_Sync/upload_payload.json \
  --course-id <UUID> \
  --dry-run

# With "course" block in payload (no --course-id):
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py" \
  --payload 05_LMS_Sync/upload_payload.json \
  --dry-run
```

Dry run output shows: section count / lesson count / topic count, and any pending placeholder warnings. If a `"course"` block is present, it prints `"Would create new course shell: <title>"`. No API calls are made.

---

## Step 4 — Check for pending placeholders (optional strict mode)

To abort if any unresolved placeholders are present:

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py" \
  --payload 05_LMS_Sync/upload_payload.json \
  --course-id <UUID> \
  --check-pending
```

This flag causes the uploader to exit with an error if `PENDING_CDN_UPLOAD` or `WISTIA_MEDIA_ID_HERE` are found in any topic body.

---

## Step 5 — Upload

```bash
# Upload to an existing shell:
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py" \
  --payload 05_LMS_Sync/upload_payload.json \
  --course-id <UUID>

# Create shell + upload in one command (payload must have a "course" block):
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py" \
  --payload 05_LMS_Sync/upload_payload.json
```

The uploader will:
1. Detect course type (MicroCourse vs standard)
2. Create sections → fetch server IDs
3. Create lessons → fetch server IDs
4. Create topics in batches of 5

### Legacy interactive mode

Calling `ti_uploader.py` with **no arguments** falls back to interactive prompts (legacy behaviour — maintained for backward compatibility):

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py"
# Prompts: payload path, course ID
```

---

## Payload JSON format (standardised)

Every convert script must produce this structure:

```json
{
  "sections": [
    {
      "title": "Section Title",
      "lessons": [
        {
          "title": "Lesson Title",
          "topics": [
            {
              "title": "Topic Title",
              "type": "text",
              "body": "<h1>...</h1><p>HTML content</p>"
            }
          ]
        }
      ]
    }
  ]
}
```

**Optional: create the shell automatically.** Add a top-level `"course"` block and omit `--course-id` — the script calls `POST /incoming/v2/content/course/create` first, captures the returned UUID, then runs the normal upload phases against it.

- `kind` defaults to `"courseGroup"` if omitted.
- `sku` must be unique in your TI instance.
- The `"course"` block is ignored if `--course-id` is passed explicitly.

### Standard course (`kind: courseGroup`)

```json
{
  "course": {
    "title": "Introduction to Marketing",
    "sku": "MKT-101",
    "kind": "courseGroup",
    "description": "Learn the fundamentals of modern marketing.",
    "metaTitle": "Introduction to Marketing | Celonis Academy",
    "metaDescription": "Master modern marketing fundamentals in this hands-on course.",
    "customFields": {
      "duration": "1h",
      "level": "Beginner",
      "product": ["Studio", "Action Flows"],
      "role": ["Data Analyst"]
    },
    "discussionsEnabled": true
  },
  "sections": [...]
}
```

### Video kind course (`kind: video`)

Video courses have no sections/lessons — they consist of a single embedded video plus optional text content. Leave out the `"sections"` key entirely.

```json
{
  "course": {
    "title": "Build Custom Visualizations Using Vega",
    "sku": "Video_WhatIsVega_EN",
    "kind": "video",
    "videoAsset": "wi27fz29of",
    "description": "Build custom JSON charts in Views.",
    "metaTitle": "Build Custom Visualizations Using Vega | Celonis Academy",
    "metaDescription": "Master custom data visualization in Celonis. Learn to build advanced charts using Vega-Lite and Vega JSON configurations.",
    "customFields": {
      "duration": "<30min",
      "level": "Intermediate",
      "product": ["View"],
      "role": ["Data Analyst"]
    },
    "articleVariant": {
      "body": "<p>Body text that appears below the video in TI admin.</p>"
    }
  }
}
```

**Field reference for the `"course"` block:**

| Field | Type | Notes |
|---|---|---|
| `title` | string | Required. The course title shown in the catalog. |
| `sku` | string | Required. Must be unique in your TI instance. |
| `kind` | string | `"courseGroup"` (default) or `"video"`. |
| `videoAsset` | string | Wistia media ID. Only for `kind: video`. |
| `description` | string | Catalog short description (~70 chars). |
| `metaTitle` | string | SEO meta title for the course group page. |
| `metaDescription` | string | SEO meta description (≤ 155 chars). |
| `customFields.duration` | string | One of: `<30min`, `30min`, `30min - 1h`, `1h`, `1h - 1h 30`, `1h - 3h`, `3h+` |
| `customFields.level` | string | One of: `Beginner`, `Intermediate`, `Advanced` |
| `customFields.product` | array | Feature filter. Values: `Studio`, `Action Flows`, `Data Integration`, `AI`, `Apps`, `View`, `Analysis`, `PQL`, `OCPM`, `CPM` |
| `customFields.role` | array | Audience filter. Values: `Data Analyst`, `Data Engineer`, `Value Architect`, `Transformation Lead`, `Project Manager`, `Celonis (CoE) Lead`, `Process Lead`, `Business User`, `Account Lead`, `Champion` |
| `articleVariant.body` | string | HTML body shown below the video. **Can only be set at creation — cannot be updated via the Incoming API after the course is created.** |

**What cannot be set via the Incoming API:**

- **`source`** (Estimated Duration, in minutes) — set manually in TI admin after creation.
- **Tags and ribbon** — use `/update-TI-course-metadata` after upload.
- **`headline`, `subtitle`, `copyright`** (variant fields visible in TI admin) — the `/learn/articles/` endpoint that controls these requires browser session auth and is not accessible via the Incoming API Bearer key.

**`preTextBlock` / `postTextBlock` (video courses):** Text rendered above/below the video player. These persist via PUT and can be set or updated after creation:

```json
{
  "courseAttributes": {
    "topics": [{"id": "<topic-uuid>", "preTextBlock": "<p>Above video</p>", "postTextBlock": "<p>Below video</p>"}]
  }
}
```

**Body cleaning:** The uploader automatically strips time indicators like `[01:00]`, `[5 min]`, `[10 mins]` from topic bodies.

---

## Step 6 — Upload internals (reference)

The TI Incoming API v2 does NOT support nested creation in a single call. `ti_uploader.py` follows the mandatory iterative pattern:

### Phase 0: Detect course type

```
GET /incoming/v2/courses/{courseId}/sections
```

- Exactly 1 section titled "Main" + 1 lesson → **MicroCourse mode** (skip phases 1–2, push topics directly)
- Otherwise → **Standard course mode**

### Phase 1: Create sections → fetch IDs

```
PUT /incoming/v2/content/course/update
Body: {"courseAttributes": {"sections": [{"courseId": "<id>", "title": "..."}, ...]}}
```

Wait 1.5 s, then `GET /incoming/v2/courses/{courseId}/sections` to fetch server-assigned IDs.

### Phase 2: Create lessons → fetch IDs

```
PUT /incoming/v2/content/course/update
Body: {"courseAttributes": {"lessons": [{"sectionId": "<phase-1-id>", "title": "..."}, ...]}}
```

Wait 1.5 s, then `GET /incoming/v2/courses/{courseId}/lessons`.

### Phase 3: Create topics (batches of 5)

```
PUT /incoming/v2/content/course/update
Body: {"courseAttributes": {"topics": [{"lessonId": "<phase-2-id>", "title": "...", "type": "text", "body": "..."}, ...]}}
```

### Chunking limits

- Sections / lessons: max 25 per request
- Topics: max 5 per request (large HTML bodies)

### API details

- Auth header: `Authorization: Bearer {api_key}`
- Content-Type: `application/json`
- Success codes: 200, 201, 204
- All endpoints relative to `TI_BASE_URL`

---

## Step 7 — Report results

Show:
- Number of sections, lessons, and topics created
- Any warnings (missing IDs, duplicate titles, API errors)
- Confirmation upload completed

Do NOT surface credentials or API keys in the output.

> **Next step:** Run `/update-TI-course-metadata` to set the catalog description, audience tags,
> duration, level, feature, role, and ribbon before the course goes live.

---

## Troubleshooting

| Issue | Fix |
|---|---|
| 403 Forbidden | Check `TI_API_KEY` is set and has full API rights |
| Topics not appearing | Verify lesson IDs were fetched correctly in Phase 2 |
| `PENDING_CDN_UPLOAD` in payload | Run image_uploader.py + patch_cdn_urls.py first |
| `WISTIA_MEDIA_ID_HERE` in payload | Replace with real Wistia media IDs before uploading |
| Duplicate sections/lessons | Script handles duplicates by order of occurrence — verify payload structure |
