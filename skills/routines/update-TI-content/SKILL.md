---
name: "update-TI-content"
description: "Update a specific topic, lesson, or section in Thought Industries by UUID — for targeted fixes and edits without re-running the full upload."
---

# Update TI Content

Targeted update of one or more topics, lessons, or sections in TI using their UUIDs. Use this
when a course is already live and you need to fix a specific page, rename a lesson, or correct
body HTML without re-uploading the whole course.

**A topic is any individual page within a course** — a text/HTML page, a video page, a PDF
page, an audio page, or any structured interactive page. Topics live inside lessons, which live
inside sections. This skill can update a topic in ANY course, including large multi-section
courses with many lessons.

**Prerequisite:** you must know the UUID of the entity to update. Use `/extract-TI-course` or
`/get-TI-course-structure` first if you don't have the IDs.

---

## Step 1 — Identify what to update

Ask the user:
1. Which course, and what specifically needs to change (topic body, lesson title, section title,
   topic position)?
2. Do they have the UUID(s) of the item(s) to update? If not, run `/get-TI-course-structure`
   first to fetch the full ID tree.

---

## Step 2 — Fetch the course structure (if UUIDs are unknown)

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/get-TI-course-structure/ti_structure.py" \
  --course-id "<course_uuid>"
```

This prints every section, lesson, and topic with its UUID. Identify the UUID(s) of the
entity or entities you want to update.

---

## Step 3 — Build the update payload

Construct the JSON payload. Include only the fields you want to change alongside the `id`.

**Update a topic's HTML body (most common use case):**
```json
{
  "courseAttributes": {
    "topics": [
      { "id": "<topic_uuid>", "body": "<p>Updated HTML content here</p>" }
    ]
  }
}
```

**Update pre/post framing text on a topic (shown above/below the main content or video):**
```json
{
  "courseAttributes": {
    "topics": [
      {
        "id": "<topic_uuid>",
        "preTextBlock": "<p>Before you start, make sure you have...</p>",
        "postTextBlock": "<p>Now that you've finished, try the next exercise.</p>"
      }
    ]
  }
}
```

**Replace the video on a topic:**
```json
{
  "courseAttributes": {
    "topics": [{ "id": "<topic_uuid>", "videoAsset": "<wistia_media_id>" }]
  }
}
```

**Rename a lesson:**
```json
{
  "courseAttributes": {
    "lessons": [
      { "id": "<lesson_uuid>", "title": "New Lesson Title" }
    ]
  }
}
```

**Update multiple topics at once:**
```json
{
  "courseAttributes": {
    "topics": [
      { "id": "<topic_uuid_1>", "body": "<p>Updated page 1</p>" },
      { "id": "<topic_uuid_2>", "title": "Fixed Title", "body": "<p>Updated page 2</p>" }
    ]
  }
}
```

Every entity **must** include its `id` UUID. The script will exit with an error if any entity
is missing an id.

### Supported topic fields

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Required |
| `title` | string | Topic title |
| `body` | string | HTML content displayed on the page (text pages, article pages, etc.) |
| `preTextBlock` | string | HTML shown above the main content or video player |
| `postTextBlock` | string | HTML shown below the main content or video player |
| `videoAsset` | string | Wistia media ID or Synthesia UUID |
| `assetType` | string | `"wistia"` (default) or `"synthesia"` |
| `videoUrl` | URL | External video URL — uploaded to Wistia by a background job |
| `caption` | string | Caption text |
| `pdfUrl` | URL | URL to PDF file |
| `audioUrl` | URL | URL to audio file (MP3/WAV/OGG, max 200 MB) |
| `posterImageAsset` | URL | Poster image shown before the video plays |
| `preAsset` | string | Wistia media ID for a pre-roll video |
| `postAsset` | string | Wistia media ID for a post-roll video |
| `width` / `height` | integer | Display dimensions in pixels |
| `searchDisabled` | boolean | Exclude from search |
| `preventProgression` | boolean | Block progression until the page is completed |
| `embeddedEnabled` | boolean | Allow embedded display |

The API accepts up to **100 total items** (topics + lessons + sections combined) per call.

---

## Step 4 — Dry run (confirm before applying)

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/update-TI-content/ti_updater.py" \
  --json '<payload_json_here>' \
  --dry-run
```

Or using a file:
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/update-TI-content/ti_updater.py" \
  --payload update_payload.json \
  --dry-run
```

Review the printed payload. Once confirmed, remove `--dry-run` to apply.

---

## Step 5 — Apply the update

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/update-TI-content/ti_updater.py" \
  --json '<payload_json_here>'
```

---

## Step 6 — Verify

Run `/get-TI-course-structure` or re-run `/extract-TI-course` on the same course to confirm
the change is reflected. Alternatively, visit the course manager in Academy to check the
updated page visually.

---

## Notes

- This skill only modifies existing entities — it does not create new topics, lessons, or sections.
  Use `/upload-course-to-TI` to create new structure.
- Body HTML must be clean TI-compatible HTML (same format as `/convert-course-to-html` produces).
  Do not include `<html>`, `<head>`, or `<body>` wrapper tags.
- After updating, the change is live immediately in TI. There is no staging environment.
- To update catalog-level fields (description, SEO meta title/description, tags, ribbon, duration,
  level, feature, role), use `/update-TI-course-metadata` instead. This skill handles topic body
  HTML, pre/post text, video assets, and lesson/section titles — see the field table in Step 3.
