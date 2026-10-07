---
name: "migrate-rise-export"
description: "Migrate an Articulate Rise 360 zip export into a Thought Industries (TI) course — extracts the Rise content into TI-ready HTML/JSON (or a reviewable Word doc first), resolves images via the existing CDN-upload step, and pushes via the existing TI uploader. Trigger on: 'migrate this Rise export', 'convert this Rise zip to TI', 'push this Rise course to TI', 'migrate this Articulate course'."
---

# Migrate Rise Export

Turn an Articulate Rise 360 zip export into a live Thought Industries course. This skill only does the Rise-specific **extraction** step itself; CDN image upload and the TI push are handed off to the plugin's existing `convert-course-to-html` and `upload-course-to-TI` skills rather than reimplemented — see "Assumed sibling skills" below.

**Co-located script:** `rise_extractor.py` (same folder as this SKILL.md) — parses the Rise zip directly (no round-trip through HTML), reusing the exact same block-dispatch logic for both output formats so nothing is lost between them.

**Assumed sibling skills** (must exist alongside this one, i.e. this folder should sit at `skills/routines/migrate-rise-export/` next to `skills/routines/convert-course-to-html/` and `skills/routines/upload-course-to-TI/`):
- `convert-course-to-html/image_uploader.py` + `patch_cdn_urls.py` — resolves the `PENDING_CDN_UPLOAD` placeholders this skill's output contains.
- `upload-course-to-TI/ti_uploader.py` — pushes the resulting payload to TI. It already binds only to newly-created sections/lessons (never touches pre-existing content) while still correctly supporting MicroCourse shells, course creation, `--dry-run`, and `--check-pending` — don't reimplement any of this here.

---

## Step 1 — Gather inputs

Ask the user for:
- **Path to the Rise zip export.**
- **Output format**: `html` (default — produces the TI HTML preview + payload JSON, ready to push) or `docx` (produces a reviewable Word doc only, no payload JSON yet — use this when a colleague wants to review/rework content before it goes anywhere near TI).
- **Target TI course ID** — the UUID of an existing course shell. (If none exists yet, see `upload-course-to-TI`'s own flow for creating one via a `"course"` metadata block — not handled by this skill.)

---

## Step 2 — Extract

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/migrate-rise-export/rise_extractor.py" <rise-export.zip> --output <workdir> --format html
```

This writes into `<workdir>`:
- `assets/` — every image/attachment extracted from the zip
- `<Course_Title>.html` — a human-readable preview
- `<Course_Title>_payload.json` — the TI-ready payload (sections → lessons → topics)

If `--format docx` was requested instead, this step produces only `<workdir>/<Course_Title>.docx` with every block labeled with its intended TI snippet (e.g. "Snippet: Accordion"), and the chain **stops here** — hand the doc to the reviewer and wait for their sign-off before re-running Step 2 with `--format html` on the *reworked* content.

---

## Step 3 — Resolve images (reuse `convert-course-to-html`)

The HTML/JSON from Step 2 contains `<img src="PENDING_CDN_UPLOAD" data-local="assets/<filename>" ...>` placeholders. Resolve them with the sibling skill's scripts, exactly as `upload-course-to-TI`'s own pre-flight checklist does:

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/image_uploader.py" <workdir>/assets --output <workdir>/cdn_map.json
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/patch_cdn_urls.py" <workdir>/<Course_Title>.html <workdir>/cdn_map.json
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/patch_cdn_urls.py" <workdir>/<Course_Title>_payload.json <workdir>/cdn_map.json
```

> **Cowork users:** `image_uploader.py` uses Playwright and cannot run in Cowork — switch to Claude Code desktop/CLI for this step.

Only proceed once zero `PENDING_CDN_UPLOAD` strings remain in the payload JSON.

**Other placeholders this script can emit have no automated resolver:**
- `PENDING_ATTACHMENT_UPLOAD` (file attachment blocks) — manually upload the file from `assets/` to the CDN and patch the URL in by hand.
- `PENDING_STORYLINE_UPLOAD` (an embedded Storyline interactive whose slide data couldn't be extracted) — review the original Rise block and recreate it manually; this is a fallback, not a conversion.

`ti_uploader.py --check-pending` catches both of these too (not just `PENDING_CDN_UPLOAD`), so a push will still abort rather than publish a broken link — but resolving them is on you, not a script.

---

## Step 4 — Review

Show the user the HTML preview (or open it) and get a go-ahead before pushing. This is the last checkpoint before the course becomes live content.

---

## Step 5 — Push (reuse `upload-course-to-TI`)

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/upload-course-to-TI/ti_uploader.py" --payload <workdir>/<Course_Title>_payload.json --course-id <TI_COURSE_ID> --check-pending
```

`--check-pending` aborts the push if any placeholder survived Step 3 — treat that as a sign Step 3 was skipped or failed, not something to override.

Report the result (sections/lessons/topics created) and the course ID back to the user.

---

## Notes

- This skill never calls the TI API directly and never uploads an image itself — all of that is delegated to the two sibling skills above, which are already correct and already maintained. If a future TI API or CDN-upload behavior needs to change, change it there, not here.
- `rise_extractor.py` has no "update existing course" merge mode and no interactive batch mode — it is extraction only, one zip at a time. Section/lesson isolation on push is handled entirely by `ti_uploader.py`.
