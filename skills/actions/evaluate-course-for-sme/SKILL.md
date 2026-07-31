---
name: "evaluate-course-for-sme"
description: "Two-phase SME (Subject Matter Expert) review: (1) Claude pre-analyzes the course to flag technical claims and accuracy risks using any reference resources the content owner provides, then (2) facilitates the human SME review via Google Docs, collects feedback, and applies approved corrections. Trigger on requests like \"run an SME review on this\", \"get this reviewed by the SME\", \"flag the technical claims in this script\", \"prepare this for expert review\"."
---

# Evaluate Course for SME

Two-phase SME review workflow. Claude first pre-analyzes the course to surface technical claims and accuracy risks (Phase 1), then prepares materials for a human SME to review, collects their feedback, and applies approved corrections (Phase 2).

**What you can give this skill:** a course script as a Google Doc link, an uploaded/downloaded file (e.g. `.docx`), or an existing live Academy course (name, URL, or UUID/slug). Optionally: reference resources for Phase 1 (Celonis documentation URLs, course files, any docs the content owner points to).

---

## When to use

Trigger on requests like: "run an SME review on this", "get this reviewed by the SME", "flag technical claims", "prepare this for expert review", "check the technical accuracy".

Run after the script is substantively complete. The SME review is focused on **technical accuracy** — not instructional design (use `/evaluate-course-for-id` for that) or persona fit (use `/evaluate-course-for-persona` for that).

---

## Prerequisites

- For existing live courses: the user's own Celonis Academy / Thought Industries API credentials must be configured for `extract-TI-course` to work.
- For Google Doc scripts: the Google Drive MCP must be connected.
- The SME's name and contact info (email or Slack) — needed to share the review doc in Phase 2.

---

## PHASE 1 — Pre-analysis

### Step 1 — Confirm scope and reference resources

Ask the user:
1. The source: Google Doc link, uploaded/local file, or existing Academy course identifier.
2. Who the SME is (name/role) and what domain they're covering.
3. Which reference resources to use for the pre-analysis — e.g.:
   - "Use the Celonis Process Mining documentation" (fetched via `/fetch-celonis-docs`)
   - "Check against [specific course name/URL]" (fetched via `extract-TI-course`)
   - "Here's the product spec doc" (uploaded by user)
   - "No external resources — just flag anything that looks like a factual claim"

   If the user says no resources: Claude still runs the pre-analysis but cannot verify claims — it flags them for the SME rather than confirming/denying.

Do not proceed to load content until scope is confirmed.

---

### Step 2 — Load course content and reference resources

- **Google Doc:** read via Google Drive MCP.
- **Uploaded/local file:** extract with `pandoc -t markdown` for `.docx`, or read directly.
- **Existing live course:** use `extract-TI-course` by UUID/slug/URL.
- **Reference resources:** load each resource specified by the user:
  - Celonis docs: use `/fetch-celonis-docs` for the relevant section(s)
  - Other courses: use `extract-TI-course`
  - Uploaded files: read directly
  - URLs: fetch via browser/web tool if available

---

### Step 3 — Pre-analyze for technical claims

Read through the course content and identify:

1. **Factual claims** — specific, verifiable statements about how Celonis products work, performance characteristics, or feature capabilities. Quote each claim verbatim with its location (section/topic heading).

2. **Procedural steps** — step-by-step instructions or workflows. Flag any step that could be wrong, outdated, or platform-specific.

3. **Definitions** — technical terms defined in the course. Flag if the definition appears incomplete, imprecise, or inconsistent with reference resources.

4. **Examples and scenarios** — flag if they appear oversimplified, potentially misleading, or inconsistent with how the product actually works.

5. **Omissions** — if reference resources reveal important concepts, caveats, or edge cases that the course does not address and should.

For each flagged item:
- Rate severity: **🔴 High** (likely incorrect or misleading), **🟡 Medium** (uncertain, may need clarification), **🟢 Low** (minor — could be more precise)
- If a reference resource was loaded: note whether the resource confirms, contradicts, or is silent on the claim
- Generate a specific verification question for the SME (e.g. "Is this step still accurate for v24.3+?", "Is the 30-second figure correct or approximate?")

For items that could not be checked against any reference resource: mark ⚪ Unverifiable from available sources.

---

### Step 4 — Save the pre-analysis

Save the pre-analysis as Markdown to `reviews/<course-name>_sme-preanalysis_<YYYY-MM-DD>.md`. Create the `reviews/` folder if it doesn't exist.

Pre-analysis structure:

```
# SME Pre-analysis — <Course Name>
**Date:** <date>
**SME domain:** <domain>
**Reference resources used:** <list or "none">

## Summary
<2–3 sentences: how many claims flagged, distribution by severity, overall impression>

## Flagged items (by severity)

### 🔴 High priority — likely needs correction
- **[Short label]** — "[verbatim quote]" ([location])
  - Issue: <what may be wrong>
  - Reference: <what the reference resource says, or "not found in loaded resources">
  - SME question: <specific question to ask>

### 🟡 Medium priority — needs clarification
...

### 🟢 Low priority — minor precision improvements
...

### ⚪ Unverifiable (no reference resource loaded for this area)
...
```

Tell the user: "Pre-analysis complete — N items flagged ([X] high, [Y] medium, [Z] low). Full pre-analysis saved to `reviews/<filename>`. Ready to prepare the SME review doc?"

Wait for confirmation before starting Phase 2.

---

## PHASE 2 — SME facilitation

### Step 5 — Prepare the SME review document

Create a Google Doc for the SME (following the same pattern as `review-course-draft`):

1. Ask the user to create a new Google Doc titled: `[SME REVIEW] <Course Name> — <date>`
2. Ask the user to enable Markdown in Google Docs if not already done (Tools → Preferences → Enable Markdown).
3. Output the full course content as Markdown. Instruct the user:
   > Copy the content above and paste via **"Paste from Markdown"** (right-click in the Doc).

4. Ask the user to prepend this SME review brief at the top of the doc:

```
SME REVIEW BRIEF
─────────────────────────────────────────────────────
Course: <Course Name>
Review focus: Technical accuracy
Reviewer: <SME name/role>

PRIORITY ITEMS TO CHECK (from pre-analysis):
<List of High and Medium flagged items — short version>

HOW TO REVIEW:
• Use Google Docs native comments (Ctrl+Alt+M / ⌘+Option+M) on specific text.
• For each flagged item, confirm correct / needs correction / needs clarification.
• For corrections: suggest the right wording in your comment.
• When done, share the doc link back.
─────────────────────────────────────────────────────
```

Share the doc with the SME.

---

### Step 6 — Wait for SME feedback

Tell the user: "Share the Google Doc with your SME. When they're done, ask them to share the doc link back, or paste their key comments here."

---

### Step 7 — Collect and process feedback

When the SME's feedback arrives:

**If given a Google Doc link:** use the Google Drive MCP to read the document body. Any comments the SME left as inline body text will appear. For sidebar comments, ask the SME to paste the key ones.

**If given pasted feedback:** work with what was provided.

For each piece of SME feedback:
1. Map it to the corresponding claim/location in the draft.
2. Propose a specific correction:
   - Quote what the course currently says
   - Show the proposed replacement (incorporating the SME's guidance)
3. Flag items that need the content author's judgment (structural changes, cases where the SME's correction affects multiple places).
4. Present the full correction plan and ask the user to approve, adjust, or skip each item.

---

### Step 8 — Apply approved corrections

Edit the local draft file directly with approved corrections. Summarise what was changed vs. skipped. If further review cycles are needed, offer to repeat from Step 5.

---

## Known limitations

- Phase 1 quality depends entirely on which reference resources are loaded. Without resources, Claude can only flag *potential* claims — it cannot verify them.
- Sidebar comments in Google Docs are not readable via the MCP. Ask the SME to use inline comments or paste key points into chat.
- This skill covers technical accuracy only. For instructional design quality, use `/evaluate-course-for-id`. For persona fit, use `/evaluate-course-for-persona`.
