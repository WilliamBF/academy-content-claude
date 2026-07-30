---
name: "browse-TI-catalog"
description: "List courses from the TI catalog with their slugs and UUIDs — useful for finding a course ID before running extract-TI-course, get-TI-course-structure, or update-TI-content."
---

# Browse TI Catalog

List course groups from the Thought Industries catalog with their slugs, IDs, and course UUIDs.
Use this when you need to find a course's UUID and only know its name.

---

## Step 1 — Run the catalog browser

List all courses (cursor-based pagination, up to 250 by default):
```bash
python "$CLAUDE_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py"
```

Search by name keyword:
```bash
python "$CLAUDE_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" \
  --search "<keyword>"
```

Raise the fetch limit for large catalogs:
```bash
python "$CLAUDE_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" \
  --limit 500
```

---

## Step 2 — Present the results

Show the user the matching course groups. Each entry displays:
- Course group title
- Slug (for use with `/extract-TI-course --slug`)
- Course group ID
- Course UUID (for use with `/extract-TI-course --course-id`, `/get-TI-course-structure`,
  `/update-TI-content`)

Point out the `course_id` field — that's the UUID needed for all content operations.
