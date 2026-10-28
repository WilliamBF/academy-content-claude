---
name: "browse-TI-catalog"
description: "List courses from the TI catalog with their slugs and UUIDs — useful for finding a course ID before running extract-TI-course, get-TI-course-structure, or update-TI-content."
---

# Browse TI Catalog

List course groups from the Thought Industries catalog with their slugs, IDs, and course UUIDs.
Use this when you need to find a course's UUID and only know its name.

The script queries `GET /incoming/v2/content?types[]=courseGroups` (100 rows per page, cursor
pagination) and reaches the whole catalog. Searching is done server-side, so a keyword search
covers every course group, not just the first page(s).

---

## Step 1 — Run the catalog browser

Search by name (preferred). Keywords are case-insensitive, all must appear in the title, and each
matches as a word prefix (`proc analy` finds "Process Analytics"):
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" \
  --search "<keywords>"
```

Search beyond the title — `--text` searches every field (title, description, slug, tags such as
"Owner <name>", custom fields); all terms must match:
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" \
  --text "<keywords>"
```

Search a specific field with `--query` (raw OpenSearch syntax, combinable with the other flags).
Verified examples: `level:Intermediate`, `duration:30min`, `slug.analyzed:<word>`,
`description.analyzed:<word>`, `"Owner Jane Doe"` (quoted tag text). Use the `.analyzed` suffix for
case-insensitive field matches; plain `field:value` is case-sensitive. Leading wildcards don't work.
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" \
  --query "level:Intermediate" --status published
```

Only published groups (hides drafts and archived):
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" \
  --search "<keywords>" --status published
```

List without a search (first 250 in the API's default order, which is most recently updated first).
Use `--limit 0` for the entire catalog (about 3,000 groups, ~30 API calls):
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/browse-TI-catalog/ti_catalog.py" --limit 0
```

Course UUIDs need one extra API call per group, so they are only looked up when 15 or fewer
groups are listed (change with `--course-ids-max N`). If a search is too broad, narrow it.

---

## Step 2 — Present the results

Show the user the matching course groups. Each entry displays:
- Course group title
- Slug (for use with `/extract-TI-course --slug`)
- Course group ID
- Course UUID, shown as `course_id` (for use with `/extract-TI-course --course-id`,
  `/get-TI-course-structure`, `/update-TI-content`). A group with several sessions shows
  `course_id[0]`, `course_id[1]`, and so on.
- Status (`published`, `draft`, `archived`)

Point out the `course_id` field — that's the UUID needed for all content operations. If it is
missing because too many groups matched, re-run with a narrower `--search`.

If the script ends with an `[ERROR]` line, the groups printed above it are still valid; the
error says why the listing stopped early.
