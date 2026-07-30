---
name: "create-course-project"
description: "Create a standard course project folder structure (01_Source_Material, 02_Drafts, 03_HTML, 04_Assets, 05_LMS_Sync) under courses/."
---

# New Course Project — Folder Structure

Create a standard course project folder structure in the workspace.

---

## Step 1 — Ask for the project name

Ask the user: "What should the project folder be called?" (e.g. `connect-and-extract`, `transform-data`). Use lowercase with hyphens.

---

## Step 2 — Create the folders

Create the following directory structure under `courses/` in the workspace:

```
courses/<project-name>/
  01_Source_Material/
    LMS_Reference/
  02_Drafts/
  03_HTML/
  04_Assets/
  05_LMS_Sync/
```

Use `mkdir -p` via bash to create all directories at once.

---

## Step 3 — Confirm

Tell the user the structure that was created:

```
<project-name>/
  01_Source_Material/
    LMS_Reference/     <- extracted LMS courses go here
  02_Drafts/           <- Claude-generated outlines and scripts
  03_HTML/             <- converted HTML output (course-to-html)
  04_Assets/           <- generated images and diagrams
  05_LMS_Sync/         <- upload log JSON
```

---

## Notes

- `01_Source_Material` is for raw SME docs, transcripts, and screenshots.
- `LMS_Reference` inside it is for extracted courses from `lms-extract`.
- `05_LMS_Sync` will hold a JSON log tracking which modules have been uploaded and at what version.
