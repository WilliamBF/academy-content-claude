---
name: "apply-review-fixes"
description: "Turn the findings in a saved review report (ID, persona, SME pre-analysis, or a consolidated review summary) into fixes on the reviewed course script, then update the report to match. Triages findings into safe mechanical fixes, author-judgment fixes and human-only items, applies only what the author approves, and records what changed. Trigger on requests like \"apply the review fixes\", \"fix what the review found\", \"apply the safe fixes from the ID report\", or when an evaluate skill offers fixes at hand-off."
---

# Apply Review Fixes

Closes the loop after a review. The evaluate skills (`/evaluate-course-for-id`, `/evaluate-course-for-persona`, `/evaluate-course-for-sme`) and `/review-course` save a report. This skill takes that report, proposes fixes to the reviewed script, applies the ones the author approves, and updates the report so it never goes stale.

**What you can give this skill:** the path to a saved report in `reviews/` (or the consolidated review summary), and the source it was run on. If the evaluate skill just ran in this session, both are already known.

---

## When to use

- At the end of an evaluate skill's hand-off, when the author says yes to "Apply the fixes now?"
- Later, on any saved report, when the author comes back to act on it.
- From `/review-course`, once, after all selected reviews finish (see that skill's Step 5).

Do not use it to run a review. Run the matching evaluate skill first.

---

## Step 1 - Load the report and the source

1. Read the report. List each finding with its location, quoted text and suggested revision.
2. Load the source the report was run on (Google Doc via the Google Drive MCP, local file, or live course via `extract-TI-course`). If the source has changed since the report date, say so and re-check each quote still matches before proposing a fix.
3. If a finding has no concrete quote or suggestion (for example, "add a link"), keep it as author judgment rather than guessing text.

---

## Step 2 - Triage

Sort every finding into one of three groups:

| Group | What goes here | How it is handled |
|---|---|---|
| **Safe, mechanical** | Passive to active rewrites, acronym defined on first use, number format, title and heading case, terminology swaps (e.g. "trainings" to "training", "leverage" to "use"), spaced single hyphen, added `[LINK NEEDED]` or `[SME CHECK]` placeholders, a stacked callout converted to prose | One batch, one approval |
| **Author judgment** | Learning objectives, structure and ordering, widget choices, persona tone or depth changes, new examples | One at a time: quote, proposed replacement, approve / adjust / skip |
| **Human only** | Content accuracy (ID 1.2), interactive elements working (ID 2.6), SME-flagged claims awaiting SME input | Never auto-applied. Stays Open in the report with a reminder of who needs to act |

Present the triage as a short table (finding, group, one-line proposed change). Do not edit anything yet.

When a consolidated summary is the input, work through its linked reports together. If two findings touch the same text, merge them into one proposed change and apply in this order: SME corrections, then ID, then persona.

---

## Step 3 - Choose where edits go

Ask which of these applies, based on the source:

- **Google Doc:** edit the document directly once the author approves. If the Google Drive connector can only read, say so and give a copy-ready list of replacements (quote, replacement, location) instead.
- **Local file (`.docx`, `.md`):** ask whether to write a new version (`<name>_v2`, `_v3`, and so on) or edit in place. A `.docx` must be edited with a tool that preserves styling; if that is not possible, give the copy-ready list.
- **Live Academy course:** never edited by this skill. Give the copy-ready list for the author to apply in Thought Industries.

Never overwrite an existing file without one of these two choices being made.

---

## Step 4 - Apply

1. **Safe batch:** show the full list of changes (quote and replacement) and ask for a single yes, or to drop individual items. Apply the approved ones.
2. **Author judgment:** go item by item. Show the current text, the proposed replacement and the reason. The author approves, adjusts or skips. Apply as you go, or collect and apply at the end if editing a Google Doc.
3. **Human only:** list them once with the action needed. Do not change the text.

Follow the style guide (`reference/celonis_content_style_guide.md`) for every replacement. Do not introduce new claims; mark anything unverified with `[SME CHECK: ...]` or `[LINK NEEDED: ...]`.

---

## Step 5 - Update the report

Keep the original findings. Do not delete or rewrite them.

1. Add a **Status** to each finding: **Fixed** (with date), **Skipped** (with reason if given), **Open** (not yet addressed), or **Human check** (waiting on a person). Use a Status column in tables and a trailing `Status: ...` tag on bullets.
2. Re-rate criteria whose findings are now all Fixed (for example, an ID criterion moves from Flag or Fail to Pass, with a note "fixed <date>"). Never mark a criterion Pass because a fix was merely proposed.
3. Recompute the At-a-glance counts (and the consolidated summary's table, if there is one).
4. Add or extend a **Revision log** at the bottom of the report:

```
## Revision log
- <YYYY-MM-DD>: Applied N fixes (X safe, Y author-approved), skipped Z, M left open or awaiting human check. Edited: <file name or Google Doc link>.
```

5. If the source was copied to a new version, record the new file name in the report header.

---

## Step 6 - Hand off

Tell the author in chat:
- How many fixes were applied, skipped and left open.
- Where the edited file or doc is, and where the updated report is saved.
- Anything that still needs a human (accuracy, interactives, SME input).
- Whether a re-run of the evaluate skill is worth doing to confirm the fixes (suggest it only if fixes changed more than a few lines).

---

## Known limitations

- Direct Google Doc edits depend on what the connected Drive connector allows. If it cannot edit, the skill falls back to a copy-ready list.
- Editing `.docx` files in place can lose styling. Prefer a new version or a copy-ready list when in doubt.
- Fixes to wording do not prove factual accuracy. The SME review stays the authority on technical claims.
