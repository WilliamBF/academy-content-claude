---
name: "extract-local-resources"
description: "Extract text, tables, slide notes, and embedded images from local source documents (PPTX, PDF, DOCX, MD, TXT) into a structured dump for use as course source material."
---

# Extract Local Resources

Pull content out of local source files — PowerPoints from SMEs, PDF spec sheets, Word docs —
into a structured `extracted.json` plus an `assets/` folder of extracted images. Use this
when source material arrives as files rather than as Celonis docs pages.

The output feeds directly into `/design-course-content` (paste or attach `extracted.json` as
context) or `/write-course-script`.

---

## Step 1 — Identify source files

Ask the user to provide the full paths to the source files. Supported formats:
- `.pptx` — slide text, tables, speaker notes, embedded images
- `.pdf` — page text and cropped images (requires `pdfplumber`; falls back to `pypdf` for text only)
- `.docx` — paragraphs, tables, embedded images (falls back to `pandoc` if `python-docx` unavailable)
- `.md` / `.txt` — read directly, no special libraries needed

---

## Step 2 — Set the output directory

Default: `courses/<course-name>/01_Source_Material/extracted/`

Create the folder if it doesn't exist.

---

## Step 3 — Install optional dependencies

Only needed for the richer formats (PPTX / PDF / DOCX). Skip if the user only has MD/TXT files.

```bash
pip install python-pptx pdfplumber pypdf python-docx --break-system-packages -q
```

---

## Step 4 — Run the extractor

```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/extract-local-resources/extract_resources.py" \
  "<output_dir>" \
  "<file1>" "<file2>" ...
```

**Example:**
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/extract-local-resources/extract_resources.py" \
  "courses/my-course/01_Source_Material/extracted" \
  "/path/to/deck.pptx" \
  "/path/to/spec.pdf"
```

---

## Step 5 — Report results

After the script runs, tell the user:
- How many files were processed and how many were skipped
- Total text blocks and images extracted per file
- Where `extracted.json` and `assets/` were saved

Then read `extracted.json` briefly and summarise what each source file contains — this gives
the user confidence the right content was captured before they move on to course design.

---

## Step 6 — Note about extracted images

Images are saved locally in `assets/<file-slug>/`. To use them in a Thought Industries course:
1. They need to be uploaded to the TI CDN — use `/convert-course-to-html` (which runs the
   image uploader) once the course HTML is ready
2. Or they can be hosted externally and referenced by URL

Do not delete the `assets/` folder — it's needed by the image upload step.

---

## Output files

| File | Contents |
|---|---|
| `extracted.json` | `{resources:[{name, ext, blocks:[...], images:[...]}]}` — one entry per source file |
| `assets/<file-slug>/<image>` | Extracted image binaries |
| `images_manifest.json` | Flat list of all images across all files: `[{file, source, bytes}]` |

Each block in `blocks` has a `kind` field: `text`, `table`, `slide_start`, or `notes` (PPTX only).
