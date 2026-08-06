---
name: "update-TI-course-metadata"
description: "Update the course-group-level metadata (description, meta title / description, custom fields, tags, ribbon) of an existing Thought Industries course shell. Drafts new copy from the course script where possible, asks the LXD to approve before writing, and never touches sections / lessons / topics. Does NOT create new course shells - use a separate creation skill for that."
---

# Update TI Course Metadata

Populate or update the catalog- and detail-page-level metadata for a Thought Industries course
shell that **already exists**. Use this right after a course shell has been created (empty), or
whenever an existing course needs its description / SEO copy / classification updated.

This skill only writes course-group metadata. It does NOT create courses, does NOT modify
sections / lessons / topics, and does NOT upload images. For those, see
`/upload-course-to-TI`, `/update-TI-content`, and the image workflow in `/convert-course-to-html`.

**Co-located script:** `ti_metadata_updater.py` — resolves credentials, translates human-readable
inputs to API field names, dry-runs before writing, and re-reads the course after the write to
show what actually changed.

**Co-located taxonomy cache:** `ti_taxonomy.json` — maps human-readable audience tag names and
owner tag names to their UUIDs, lists valid custom-field option values, and lists valid ribbon
slugs. Update this file when Celonis Academy adds new tags / options in the TI admin UI.

---

## What this skill sets

Confirmed writable via `PUT /incoming/v2/content/course/update` (verified 2026-07-27 against a
live course):

| Field | UI location | Notes |
|---|---|---|
| `description` | Basic info | Nicole's house rule: ≤100 characters, imperative, "what's in it for me" framing. The API allows up to 5000, but the skill enforces 100. |
| `metaTitle` | SEO | Fixed template: `[Course Title] \| Celonis Academy`. |
| `metaDescription` | SEO | ≤155 characters, active voice, call-to-action, keyword-rich, matches page content. See `Meta description good practices` on Confluence. |
| `customFields` | Design Settings > Custom Fields | Human-readable string values, not UUIDs. Keys: `duration`, `level`, `product` (UI label: "Feature"), `role`. Arrays for multi-select (`product`, `role`), strings for single-select (`duration`, `level`). |
| `tagIds` | Design Settings > Tags | Array of tag UUIDs. Skill translates human names ("partner", "Owner Nicole Wendler") to UUIDs via `ti_taxonomy.json`. |
| `ribbon` | Design Settings > Ribbon | Slug string, one of `new`, `updated`, `internal`. Skill accepts either display name ("New!") or slug. Pass `null` to clear. |

## What this skill does NOT set (and why)

- **`source`** (Advanced Settings > Source — approximate duration): the API rejects every value
  we've tried, including strings other courses have stored, with `HTTP 400: A processing error
  occurred`. Suggests the field is read-only via this endpoint, or requires a different
  endpoint we haven't found. **Instruct the LXD to set this manually in the TI admin UI.**
  Recommend Nicole raise this as a feature request with TI.
- **Learning Objectives tab** (Detail Page Settings > Tabs): no field for arbitrary
  detail-page tabs in the metadata endpoint. Set manually in the TI admin UI.
- **`asset` / `detailAsset`** (catalog + detail images): out of scope for v1 - handled by the
  image workflow.
- **`title` / `slug`**: presumed already correct on the shell. If they need to change, add them
  to the payload manually — the script accepts them but does not draft them.

---

## Credentials

`ti_metadata_updater.py` resolves credentials automatically via `lib/config.py`. Credentials are never printed.

| Setup | Where | Works in Cowork? | Notes |
|---|---|---|---|
| Plugin install folder | `{plugin_root}/secrets.env` | ✓ | Recommended — set once, persists across sessions and updates |
| Workspace root | `secrets.env` in opened folder | ✓ | Per-project |
| Any ancestor folder | `secrets.env` in a parent folder | ✓ | Found by walking up from CWD |
| `settings.json` | `"env"` block (no file) | ✓ | Claude Code native, no file needed |
| Home directory | `~/.claude/secrets.env` | ✗ | Desktop only, ephemeral in Cowork |

Required variables: `TI_BASE_URL`, `TI_API_KEY`. Run `python setup.py` to check which location was found.

---

## Step 1 — Identify the course

Ask the LXD for **either** identifier - the script auto-resolves whichever is provided:

- **Course Group ID** (what the metadata endpoint actually needs), or
- **Course UUID** (what `/upload-course-to-TI` and `/get-TI-course-structure` use — script
  looks it up in the catalog and finds the parent Course Group ID via `displayCourseId`)

If the LXD doesn't have either, run `/browse-TI-catalog --search "<partial title>"` first.

---

## Step 2 — Fetch the current state

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/update-TI-course-metadata/ti_metadata_updater.py" \
  --course-id "<either-ID>" \
  --show-current
```

Prints every current field value (description, metaTitle, metaDescription, customFields, source,
ribbon, etc.) so the LXD can see the baseline. Note: `tagIds` is not returned by the GET
endpoint even when tags are set — this is a TI API omission, not a bug. Trust the write, verify
tag application visually in the admin UI.

---

## Step 3 — Draft the copy (description, metaTitle, metaDescription)

If a course script exists locally (e.g. `courses/<slug>/02_Drafts/<slug>.md`), read it and
propose:

1. **`description`** — one imperative sentence, ≤100 characters, answering "what's in it for
   me?". Ask the LXD if there's a keyword that must appear (e.g. "MCP" for the Agent Tools
   course). Draft two alternatives so the LXD can pick.

2. **`metaTitle`** — always `[Course Title] | Celonis Academy`, using the exact course title.

3. **`metaDescription`** — ≤155 characters, active voice, includes a call-to-action, keyword-
   rich, matches the page content. Per the Confluence "Meta description good practices" page:
   - Put yourself in the learner's shoes; think of what they'd search for.
   - Active voice, include a CTA.
   - Include as many keywords / synonyms as you can.
   - Match the content of the page.
   - Never write random individual words - search engines will substitute a random sentence
     from page content otherwise.

**Show the drafts to the LXD and get explicit approval before proceeding.** Never PUT copy the
LXD hasn't seen.

---

## Step 4 — Gather structured fields

Ask the LXD for the custom-field values, using the option lists in `ti_taxonomy.json`:

- **`duration`** (single-select): `<30min`, `30min`, `30min - 1h`, `1h`, `1h - 1h 30`,
  `1h - 3h`, `3h+`.
- **`level`** (single-select): `Beginner`, `Intermediate`, `Advanced`.
- **`product`** — UI label **"Feature"** (multi-select): `Studio`, `Action Flows`,
  `Data Integration`, `AI`, `Apps`, `View`, `Analysis`, `PQL`, `OCPM`, `CPM`.
- **`role`** (multi-select): `Data Analyst`, `Data Engineer`, `Value Architect`,
  `Transformation Lead`, `Project Manager`, `Celonis (CoE) Lead`, `Process Lead`,
  `Business User`, `Account Lead`, `Champion`.

Suggest sensible defaults based on the course content, but let the LXD confirm.

---

## Step 5 — Handle tags carefully (visibility warning)

**Audience tags directly control who sees the course in the catalog.** Setting `partner`,
`customer`, `public`, or `internal` makes the course *immediately visible* to everyone in that
group logged into Academy. Handle with extreme care.

Recommended flow:

1. **Default**: only apply the LXD's Owner tag. Do not apply any audience tag automatically.
2. **If the LXD asks for `academy`**: this is a low-risk audience tag (Academy-only visibility).
   Apply on confirmation.
3. **If the LXD asks for `internal`, `public`, `customer`, `partner`, or `academic`**: print a
   loud warning explaining what visibility this triggers, then require an explicit "yes, I
   want <tag> to make this visible to <audience>" before writing.

The Owner tag is safe - it does not affect visibility. Auto-suggest the LXD's own Owner tag
based on the taxonomy cache; ask which owner if unclear.

---

## Step 6 — Ribbon (optional)

Valid ribbon slugs: `new`, `updated`, `internal`. Ask the LXD whether the course needs a
ribbon. Common defaults:

- New course being launched → `new` (display: "New!")
- Substantial re-release → `updated`
- Otherwise → omit or set to `null`

The script accepts either the display name or the slug and translates.

---

## Step 7 — Dry run

Assemble the full payload and show the exact JSON that will be PUT. Do NOT include unchanged
fields - the API preserves any field not present in the payload, so a targeted update is safer
than a full-object replace.

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/update-TI-course-metadata/ti_metadata_updater.py" \
  --course-id "<either-ID>" \
  --payload metadata_payload.json \
  --dry-run
```

Or pass the payload inline as JSON via `--json '<...>'`. The dry run prints:

- The resolved Course Group ID (with a note if the input was a Course UUID that got resolved).
- The exact PUT body that would be sent.
- Any validation warnings (e.g. description over 100 chars, unknown custom-field option,
  audience tag not confirmed).

---

## Step 8 — Apply

After the LXD approves the dry-run output:

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/update-TI-course-metadata/ti_metadata_updater.py" \
  --course-id "<either-ID>" \
  --payload metadata_payload.json
```

The script:
1. Resolves credentials from `secrets.env` (never prints values).
2. Sends `PUT /incoming/v2/content/course/update` with body
   `{"courseAttributes": {"courseGroups": [{"id": <groupId>, ...fields}]}}`.
3. On HTTP 200, does a follow-up `GET /incoming/v2/courseGroups/<groupId>` and prints
   which fields now match the intended values, plus which fields the API omitted from GET
   (tagIds - trust the write, verify in UI).
4. Reminds the LXD to set `source` manually in the TI admin UI (Advanced Settings > Source).

---

## Step 9 — Nudge the LXD to finalise in the UI

After a successful write, print a short checklist:

- Verify tag application in the TI admin UI (GET does not return tagIds).
- Set `source` (Advanced Settings > Source) manually — API can't write this yet.
- Add the Learning Objectives detail-page tab manually if not already there.
- Double-check the ribbon appears as expected.

---

## Payload JSON format (for `--payload <file>`)

```json
{
  "description": "One imperative sentence, ≤100 chars.",
  "metaTitle": "Course Title | Celonis Academy",
  "metaDescription": "Active-voice, keyword-rich, ≤155 chars, ends with CTA.",
  "customFields": {
    "duration": "1h - 1h 30",
    "level": "Intermediate",
    "product": ["AI", "Studio"],
    "role": ["Data Analyst", "Champion"]
  },
  "tags": ["academy", "Owner Nicole Wendler"],
  "ribbon": "new"
}
```

The script:
- Translates `tags` (human names) to `tagIds` (UUIDs) via `ti_taxonomy.json`.
- Translates `ribbon` display names ("New!") to slugs ("new").
- Validates custom-field option values against the enum lists in the taxonomy.
- Wraps the whole thing in `{"courseAttributes": {"courseGroups": [{"id": <groupId>, ...}]}}`
  before sending.

Any unknown key in the payload is passed through as-is (so you can add `title`, `slug`,
`asset`, etc. manually without waiting for a skill update - just at your own risk).

---

## Error reference

| Error | Cause | Fix |
|---|---|---|
| `HTTP 400: No items provided` | Payload missing the `courseAttributes.courseGroups` array wrapper. | Script handles automatically; if hit, the wrapper logic broke. |
| `HTTP 400: A processing error occurred` on `source` write | `source` is not writable via this endpoint. | Skip; set in UI. Consider TI feature request. |
| `HTTP 400: Invalid ribbon slug 'X'. Available ribbons: ...` | Slug not in the school's ribbon list. | The error message helpfully lists valid slugs - script surfaces this and re-prompts. |
| `HTTP 400: A processing error occurred` on other fields | Custom-field option not recognised, or invalid tag UUID. | Check the option against the taxonomy; check the tag UUID exists on `/incoming/v2/tags`. |
| Course Group ID not resolved | Wrong Course UUID, or catalog listing didn't include the course (unpublished shells sometimes don't appear). | Ask LXD for the Course Group ID directly (visible in TI admin URL). |
