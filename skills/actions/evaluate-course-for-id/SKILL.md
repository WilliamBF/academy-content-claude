---
name: "evaluate-course-for-id"
description: "Apply the Celonis Academy instructional design review checklist to a course script or live course — covering content quality & accuracy, engagement & learner experience, grammar/spelling/clarity, and language use. Produces a structured pass/flag/fail report with suggestions. Never edits the source directly. Trigger on requests like \"run an ID review on this script\", \"check this against the ID checklist\", \"review this draft for instructional design quality\"."
---

# Evaluate Course for ID

Apply the Celonis Academy instructional design review checklist to a course script or live course, and produce a structured findings report. This skill only ever *suggests* changes — it never edits the source script or live course. All suggestions are reviewed by the Learning Experience Designer before anything is changed.

**What you can give this skill:** a course script as a Google Doc link, an uploaded/downloaded file (e.g. `.docx`), or an existing live Academy course (name, URL, or UUID/slug).

---

## When to use

Trigger on requests like: "run an ID review on this script", "check this against the ID checklist", "review this draft for instructional design quality", "apply the course review checklist".

Run this review when a draft is substantively complete — after scripting but before final HTML conversion. It can also be run on an existing live course.

---

## Prerequisites

- For existing live courses: the user's own Celonis Academy / Thought Industries API credentials must be configured for `extract-TI-course` to work.
- For Google Doc scripts: the Google Drive MCP must be connected.
- For uploaded/local files: no additional setup needed.

---

## The ID Review Checklist

This checklist is embedded here — do not load it from an external file at runtime.

### 1. Content Quality & Accuracy
| # | Criterion | AI-checkable |
|---|---|---|
| 1.1 | Learning objectives are clearly stated and align with the course content | Yes |
| 1.2 | All content is accurate and up-to-date | Partial (flag for human verification) |
| 1.3 | Key concepts are explained clearly and concisely | Yes |
| 1.4 | Examples used are relevant and illustrative | Yes |
| 1.5 | No redundant or off-topic information included | Yes |
| 1.6 | Learning progression is logical and well-structured | Yes |
| 1.7 | Source references are cited appropriately (if applicable) | Yes |

### 2. Engagement & Learner Experience
| # | Criterion | AI-checkable |
|---|---|---|
| 2.1 | Content tone is appropriate for the target audience | Yes |
| 2.2 | Content encourages learner curiosity and motivation | Yes |
| 2.3 | Calls to action (reflection prompts, knowledge checks) are included where relevant | Yes |
| 2.4 | There is a balance between information and interaction (not too text-heavy) | Yes |
| 2.5 | Multimedia (images, videos, animations) enhances the learning experience | Partial (flag if absent or overused) |
| 2.6 | Interactive elements (quizzes, polls, drag & drop, etc.) function correctly | Human check required |
| 2.7 | Activities are meaningful and support learning objectives | Yes |
| 2.8 | Feedback is provided for quiz answers (especially incorrect ones) | Yes |

### 3. Grammar, Spelling & Clarity
| # | Criterion | AI-checkable |
|---|---|---|
| 3.1 | No spelling errors | Yes (with caveat: Claude is not infallible) |
| 3.2 | Grammar and punctuation are correct throughout | Yes |
| 3.3 | Sentence structure is clear and easy to read | Yes |
| 3.4 | Acronyms are defined on first use | Yes |
| 3.5 | Consistent terminology and phrasing throughout | Yes |

### 4. Language Use
| # | Criterion | AI-checkable |
|---|---|---|
| 4.1 | Language is clear, concise, and appropriate for the target audience | Yes |
| 4.2 | Tone is consistent and aligned with the course's purpose | Yes |
| 4.3 | Jargon and technical terms are explained or avoided unless necessary | Yes |
| 4.4 | Inclusive and respectful language is used | Yes |
| 4.5 | Passive voice is minimized; active voice preferred | Yes |

---

## Step 1 — Confirm scope

If not already clear from the request, ask:
1. The source: Google Doc link, uploaded/local file, or existing Academy course (name/URL/UUID/slug).
2. Whether to apply the full checklist or focus on specific categories.

Do not proceed to load content until scope is confirmed.

---

## Step 2 — Load course content

- **Google Doc:** read via the Google Drive MCP.
- **Uploaded/local file (`.docx`):** extract with `pandoc -t markdown`, or read directly if plain text.
- **Existing live course:** use the `extract-TI-course` skill (by UUID/slug/URL) to get structured Markdown. Ask for the course identifier if not provided.

---

## Step 3 — Apply the checklist

Work through each of the 25 criteria systematically. For each, assign one of three ratings:

- **✅ Pass** — criterion is clearly met; brief note why.
- **⚠️ Flag** — criterion is partially met, uncertain, or requires human verification; note what to check.
- **❌ Fail** — criterion is clearly not met; provide a concrete suggestion with quote + location.

**Criteria that always require human verification** (mark ⚠️ Human check regardless of content):
- 2.6 Interactive elements function correctly
- 1.2 Content accuracy (flag specific factual claims that could not be verified from the text alone)

For spelling/grammar (3.1, 3.2): note any specific instances found, but caveat that Claude's spell-checking is not exhaustive — a human pass is still recommended for the final draft.

---

## Step 4 — Produce the report

Save the report as Markdown to `reviews/<course-name>_id-review_<YYYY-MM-DD>.md`. Create the `reviews/` folder if it doesn't exist.

Report structure:

```
# ID Review — <Course Name>
**Date:** <date>
**Source:** <file/doc/course identifier>
**Reviewed by:** Claude (content-creation-plugin evaluate-course-for-id)

## At a glance

| Category | Pass | Flag | Fail |
|---|---|---|---|
| 1. Content Quality & Accuracy | X | X | X |
| 2. Engagement & Learner Experience | X | X | X |
| 3. Grammar, Spelling & Clarity | X | X | X |
| 4. Language Use | X | X | X |
| **Total** | **X** | **X** | **X** |

## 1. Content Quality & Accuracy

| # | Criterion | Rating | Notes |
|---|---|---|---|
| 1.1 | Learning objectives stated and aligned | ✅ / ⚠️ / ❌ | ... |
...

## 2. Engagement & Learner Experience
...

## 3. Grammar, Spelling & Clarity
...

## 4. Language Use
...

## Suggested next steps
[Short paragraph: what to fix first, what needs human verification, whether the draft is ready to proceed]
```

---

## Step 5 — Hand off

Present the At-a-glance summary table and the top 3 priority failures/flags in chat. Always say explicitly that this is a partial summary and the **full report with every criterion, quote, and suggestion is in the saved file** — give the file path.

Do not edit the original script or live course. If the user asks to apply specific suggestions, treat that as an explicit follow-up action — confirm which items to apply first.

---

## Known limitations

- Spelling/grammar checks are not exhaustive — a human proofreading pass is still recommended.
- Interactive element functionality (criterion 2.6) cannot be verified from the script text alone — always requires human testing.
- Factual accuracy (criterion 1.2) can only be partially checked; SME review via `/evaluate-course-for-sme` is the appropriate follow-up for technical claims.
