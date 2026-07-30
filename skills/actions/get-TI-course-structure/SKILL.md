---
name: "get-TI-course-structure"
description: "Fetch and display the full section/lesson/topic tree for a TI course, including entity UUIDs — useful before running update-TI-content."
---

# Get TI Course Structure

Fetch the full section → lesson → topic tree for a Thought Industries course and display every
entity with its UUID. Use this to find the IDs you need before running `/update-TI-content`.

---

## Step 1 — Get the course UUID

You need the course UUID (not the courseGroup UUID). If you don't have it:
- Use `/browse-TI-catalog` to search by course name and get the course ID
- Or check the `secrets.env` / workspace notes from a previous `/upload-course-to-TI` run

---

## Step 2 — Fetch the structure

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/get-TI-course-structure/ti_structure.py" \
  --course-id "<course_uuid>"
```

Optional — save the raw JSON for reference:
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/get-TI-course-structure/ti_structure.py" \
  --course-id "<course_uuid>" \
  --output structure.json
```

---

## Step 3 — Present the results

Show the user the tree output. Highlight the UUIDs of the sections/lessons/topics they're
interested in editing. If the user wants to update one of these items, hand off to
`/update-TI-content` with the relevant UUID(s).
