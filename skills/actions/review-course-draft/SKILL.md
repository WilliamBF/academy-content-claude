---
name: "review-course-draft"
description: "Prepare a Markdown draft for human review via Google Docs: output the content for manual 'Paste from Markdown', guide the reviewer through native comments, then collect feedback and apply approved changes to the local draft file."
---

# Review Course Draft

Manage the review cycle for a course draft. Creates a structured Google Doc for reviewers,
provides a clear feedback convention, and applies returned comments to the draft.

**Constraint:** the Google Drive MCP can create and read Google Docs but cannot add or read
sidebar comments. This skill works around that by instructing the user to paste the Markdown
draft into a new Google Doc using "Paste from Markdown" (which preserves formatting), so
reviewers can use Google Docs' native inline comments on properly structured content.

---

## Step 1 — Identify the draft to review

Ask the user:
1. Which draft file to send for review (typically `courses/<name>/02_Drafts/<filename>.md`)
2. Who the reviewer(s) are — names and/or emails to share the Doc with

Read the draft file so you have the full Markdown content ready to output.

---

## Step 2 — Prepare the review Google Doc

### 2a — Create a new blank Google Doc

Ask the user to create a new Google Doc titled: `[REVIEW] <Course Name> — <date>`

Then ask them to do a one-time setup if they haven't already:

> **Enable Markdown in Google Docs (one time):**
> Tools → Preferences → check "Enable Markdown"

### 2b — Paste the draft using Paste from Markdown

Output the full draft content as clean Markdown. Then instruct the user:

> Copy the Markdown content above, go to your Google Doc, right-click and select
> **"Paste from Markdown"**.
>
> This converts headings, bold, lists, and other formatting into proper Google Docs
> structure — reviewers see formatted content, not raw Markdown syntax.

### 2c — Add reviewer instructions at the top

Ask the user to manually prepend this block to the doc (or add it as a comment):

```
HOW TO REVIEW
─────────────────────────────────────────────────────
• Use Google Docs' native comments (Ctrl+Alt+M / ⌘+Option+M) on specific text.
• For overall structural feedback, add a comment at the section heading.
• When done, share the doc link back with the content author.
─────────────────────────────────────────────────────
```

Share the Google Doc link with the reviewer(s).

---

## Step 3 — Wait for review

Tell the user: "Share the Google Doc with your reviewer(s). When they're done, ask them to
either share the doc link back, or summarise their key comments and paste them here."

---

## Step 4 — Collect and process feedback

When the reviewer's feedback arrives (shared doc link or pasted summary):

**If given a Google Doc link:**
Use the Google Drive MCP to read the document. This reads the body text — any comments the
reviewer left as body text (not sidebar) will appear here. For sidebar comments, the reviewer
needs to describe them or paste the key ones.

**If given pasted feedback:**
Work with what the reviewer provided directly.

In either case:
1. Map each piece of feedback to the corresponding section/topic in the draft.
2. Present a proposed revision plan:
   - List each change: `Page X — [what the reviewer said] → [proposed fix]`
   - Flag items that need author judgment (ambiguous, conflicting, or major structural changes)
3. Ask the user to approve, adjust, or skip each proposed change.

---

## Step 5 — Apply approved changes

Edit the local draft file directly (`courses/<name>/02_Drafts/<filename>.md`) with the approved
changes. After editing:

- Summarise what was changed vs. skipped
- Confirm the file is ready for the next pipeline step
- If the draft needs another review cycle, offer to repeat from Step 2

---

## Notes

- **Sidebar comments** in Google Docs (the pop-out bubbles) are not readable by Claude via the
  MCP. Ask the reviewer to either paste key sidebar comments into the chat, or use the
  "Insert comment" approach for short items that would fit inline.
- **Suggestions mode** in Google Docs ("Suggesting" in the top-right toolbar) is another option
  for reviewers who want to propose specific text edits directly in the doc.
- After applying feedback, the updated draft is ready for `/write-course-script` (if the content
  still needs TI widget formatting) or `/convert-course-to-html` (if the script is already done).
