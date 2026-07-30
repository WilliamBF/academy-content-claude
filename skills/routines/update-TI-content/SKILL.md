---
name: "update-TI-content"
description: "Update a specific topic, lesson, or section in Thought Industries by UUID — for targeted fixes and edits without re-running the full upload."
---

# Update TI Content

Targeted update of one or more topics, lessons, or sections in TI using their UUIDs. Use this
when a course is already live and you need to fix a specific page, rename a lesson, or correct
body HTML without re-uploading the whole course.

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

Construct the JSON payload. Include only the fields you want to change alongside the `id`:

**Update a topic body:**
```json
{
  "courseAttributes": {
    "topics": [
      { "id": "<topic_uuid>", "body": "<p>Updated HTML content here</p>" }
    ]
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
  level, feature, role), use `/update-TI-course-metadata` instead. This skill only edits body
  HTML, lesson titles, and section structure.
