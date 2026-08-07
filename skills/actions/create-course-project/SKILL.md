---
name: "create-course-project"
description: "Create a standard course project folder structure (01_Source_Material, 02_Drafts, 03_HTML, 04_Assets, 05_LMS_Sync). Detects workspace context automatically — works whether the workspace is a parent folder, an existing course folder, or the courses collection folder itself."
---

# New Course Project — Folder Structure

Create a standard course project folder structure in the workspace.

---

## Step 1 — Detect workspace context (silent, no output yet)

Before asking anything, run these two checks:

```bash
# Check 1: pipeline folders or courses/ directly in CWD
ls -d 0*/ courses/ 2>/dev/null || true

# Check 2: subdirs whose contents include 0x_ folders (means CWD is the courses collection)
ls -d */0*/ 2>/dev/null | head -1 || true
```

Route based on results:

- **Any `0x_` folder found directly in CWD** (`01_Source_Material/`, `02_Drafts/`, etc.) → workspace IS an existing course project root → go to **Step 2a**
- **`courses/` found directly in CWD** → multi-course parent workspace → go to **Step 2b**
- **A `<subdir>/0x_` path found** (subdirectory contains pipeline folders) → workspace IS the courses collection folder → go to **Step 2d**
- **None of the above** → fresh / ambiguous workspace → go to **Step 2c**

---

## Step 2a — Fill in missing folders (workspace IS a course folder)

Do NOT ask for a project name — we're already in one. Create only the folders that are missing from the standard set, directly in CWD:

```
01_Source_Material/
  LMS_Reference/
02_Drafts/
03_HTML/
04_Assets/
05_LMS_Sync/
```

```bash
mkdir -p 01_Source_Material/LMS_Reference 02_Drafts 03_HTML 04_Assets 05_LMS_Sync
```

Go to **Step 3**.

---

## Step 2b — Standard multi-course workspace (has `courses/`)

Ask: "What should the new course project folder be called?" (e.g. `connect-and-extract`, `transform-data` — lowercase with hyphens).

Create under `courses/`:

```bash
mkdir -p "courses/<project-name>/01_Source_Material/LMS_Reference" \
         "courses/<project-name>/02_Drafts" \
         "courses/<project-name>/03_HTML" \
         "courses/<project-name>/04_Assets" \
         "courses/<project-name>/05_LMS_Sync"
```

Go to **Step 3**.

---

## Step 2c — Ambiguous fresh folder

Ask:

> "This folder doesn't have a `courses/` subfolder yet. Should I:
> 1. Create `courses/<project-name>/` here — good if you'll have multiple course projects in this workspace
> 2. Set up pipeline folders directly in this folder — if this folder IS the course project"

- **Option 1**: ask for project name → same as Step 2b
- **Option 2**: same as Step 2a (create folders directly in CWD)

Go to **Step 3**.

---

## Step 2d — Workspace IS the courses collection folder

Ask: "What should the new course project folder be called?" (lowercase with hyphens).

Create directly in CWD (no extra `courses/` prefix — we're already inside it):

```bash
mkdir -p "<project-name>/01_Source_Material/LMS_Reference" \
         "<project-name>/02_Drafts" \
         "<project-name>/03_HTML" \
         "<project-name>/04_Assets" \
         "<project-name>/05_LMS_Sync"
```

Go to **Step 3**.

---

## Step 3 — Confirm

Tell the user what was created (or already existed in Step 2a):

```
<project-name>/
  01_Source_Material/
    LMS_Reference/     ← extracted LMS courses go here
  02_Drafts/           ← Claude-generated outlines and scripts
  03_HTML/             ← converted HTML output (convert-course-to-html)
  04_Assets/           ← generated images and diagrams
  05_LMS_Sync/         ← upload payload JSON
```

---

## Notes

- `01_Source_Material` is for raw SME docs, transcripts, and screenshots.
- `LMS_Reference` inside it is for extracted courses from `/extract-TI-course`.
- `05_LMS_Sync` holds the upload payload JSON used by `/upload-course-to-TI`.
