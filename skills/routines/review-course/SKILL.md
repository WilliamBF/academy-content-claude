---
name: "review-course"
description: "Orchestrate a full course review by running any combination of the three review types — persona fit, instructional design, and SME/technical accuracy — against the same course. Loads the course content once and produces a consolidated summary linking to individual reports. Trigger on requests like \"run a full review\", \"review this course\", \"run all reviews on this script\", or when the user wants to combine two or more review types in one pass."
---

# Review Course (Full Review Orchestrator)

Runs one or more of the three course review types against the same course and produces a consolidated summary. Each review type is handled by a dedicated skill — this routine coordinates them so you don't need to invoke each one separately.

**Individual skills this routine calls:**
- `/evaluate-course-for-persona` — persona fit (AI-driven, uses Drive persona files)
- `/evaluate-course-for-id` — instructional design checklist (AI-assisted, 4-category QA)
- `/evaluate-course-for-sme` — SME / technical accuracy (pre-analysis + human facilitation)

You can also run any of those skills directly if you only need one type of review.

---

## Step 1 — Confirm which reviews to run

Ask the user:

1. **Course source:** Google Doc link, uploaded/local file, or existing Academy course (name, URL, UUID/slug).

2. **Which reviews to run** (default: all three unless the user specifies):
   - ☐ Persona review — needs: which persona(s) and which panorama (customer/partner)
   - ☐ ID review — no extra inputs needed
   - ☐ SME review — needs: SME name/role, and optionally reference resources for pre-analysis

3. For **persona review**: which persona(s) to check (e.g. "Project Manager (Customer)", "IT Lead (Partner)"). If the user says "the usual" or "the tagged persona", check the course's own metadata/tags first.

4. For **SME review**: whether to run Phase 1 only (pre-analysis, no doc prep yet) or both phases in this session.

Do not proceed until scope is confirmed. Running all three reviews on a large course is a significant operation — confirm with the user before starting.

---

## Step 2 — Load course content (once)

Load the course content using the appropriate method based on the source type:

- **Google Doc:** read via Google Drive MCP.
- **Uploaded/local file:** extract with `pandoc -t markdown` for `.docx`, or read directly.
- **Existing live course:** use `extract-TI-course` by UUID/slug/URL.

Keep this content in context for all selected reviews — do not reload it for each review.

---

## Step 3 — Run selected reviews in sequence

Run each selected review skill in sequence, passing the already-loaded course content. Follow each skill's own steps fully:

**If persona review selected:**
→ Follow `/evaluate-course-for-persona` Steps 2–6 (skip Step 3 — content already loaded).

**If ID review selected:**
→ Follow `/evaluate-course-for-id` Steps 3–4 (skip Step 2 — content already loaded).

**If SME review selected:**
→ Follow `/evaluate-course-for-sme` Steps 2–4 (Phase 1 only; skip Step 2 content loading — already done).
→ After Phase 1: pause and ask the user whether to proceed to Phase 2 (SME facilitation) now or handle it as a follow-up.

Each review saves its own full report file to `reviews/`.

---

## Step 4 — Produce consolidated summary

After all selected reviews are complete, produce a one-page consolidated summary:

```
# Course Review Summary — <Course Name>
**Date:** <date>
**Reviews run:** [Persona / ID / SME]

## Overall picture

| Review type | Outcome | Report |
|---|---|---|
| Persona — <persona name> | <one-line verdict, e.g. "Good fit, 3 medium gaps"> | [link] |
| ID checklist | <e.g. "22/25 pass, 3 flags, 0 failures"> | [link] |
| SME pre-analysis | <e.g. "8 claims flagged: 2 high, 4 medium, 2 low"> | [link] |

## Top priorities across all reviews

1. <Highest-priority cross-review finding — type, criterion, short description>
2. ...
(up to 5)

## Suggested next steps

<Short paragraph: what to fix first, what needs human follow-up, whether the course is ready to proceed to HTML conversion>
```

Save the consolidated summary to `reviews/<course-name>_review-summary_<YYYY-MM-DD>.md`.

---

## Step 5 — Hand off

Present the consolidated summary table in chat and give the user direct paths to all saved report files. If the SME review Phase 2 (doc prep and facilitation) was deferred, remind the user to run `/evaluate-course-for-sme` when ready to proceed.

---

## Notes

- **Run reviews individually when:** you only need one type of review, or when the course source is already loaded in context from a prior skill (e.g. just after `/write-course-script`).
- **Run this routine when:** you want a full QA pass before HTML conversion, or when multiple stakeholders need different review types addressed in one session.
- **Order of review types doesn't matter** for the reports themselves, but if the course needs significant content changes based on persona or ID review, it may make sense to fix those before running the SME review.
