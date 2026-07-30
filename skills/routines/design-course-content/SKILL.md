---
name: "design-course-content"
description: "Plan, outline, draft, and review any Celonis Academy training content (scripts, storyboards, lesson outlines, knowledge checks) using the team's instructional design foundations and content style guide. Use this skill at the start of any new content piece — before scripting begins."
---

# Design Course Content

This skill covers the design and drafting phase of the content pipeline — the work that happens
before scripting. It applies the team's instructional design theory (structure, sequencing,
objectives) and the Celonis content style guide (tone, naming, inclusion) at the same time.

Pair it with `/write-course-script` (TI widget production) and `/write-exam-questions`
(assessment items) once the design is approved.

---

## Step 1 — Confirm content type and source material

Ask the user two things before starting anything:

1. **Content type** — e.g. a microcourse, a video/voiceover script, a full course, a module
   outline, a knowledge check, an exam, or something else. This matters because:
   - Voiceover scripts need shorter sentences and spelled-out special characters
   - Exams have stricter format rules than regular quizzes
   - Course/module outlines need sequencing decisions a single page script doesn't
2. **Source material** — a Google Drive folder, local files, or other docs beyond the bundled
   references. Don't assume based on a past conversation — ask every time.

If invoked with no task at all (bare slash command), also ask for the topic:
> "What would you like to create, and what should it cover? What kind of content is it
> (microcourse, video script, full course, exam, etc.)? Do you have a Google Drive folder or
> local files with source material?"

If they provide a Drive folder or local files, read them before drafting.

---

## Step 2 — Load the right reference material

Three reference files are bundled with this plugin — read whichever apply to the task:

- `$CLAUDE_PLUGIN_ROOT/reference/instructional_design_foundations.md` — the theory:
  learning needs analysis, outcome-based objectives, content sequencing, Gagne's 9 events,
  the 8-step ID process, evaluation. Read this when planning structure or sequencing.
- `$CLAUDE_PLUGIN_ROOT/reference/celonis_content_style_guide.md` — the house style:
  tone, active voice, sentence length, number formatting, naming conventions, the inclusion
  checklist, voiceover rules. Read this when writing sentences or reviewing a draft.
- `$CLAUDE_PLUGIN_ROOT/reference/question_writing_guide.md` — how to write knowledge
  checks and qualification exam questions: Bloom's cognitive levels, MCQ/MRQ format rules,
  distractor writing, what's off-limits in qualification exams. Read this whenever the task
  involves any quiz or exam questions.

These are working copies of live Confluence pages. If a task turns on a detail that seems
outdated or missing, re-fetch the live page rather than trusting the cached copy.

---

## Step 3 — Draft new content

1. Confirm (or help pin down) the learning objective(s) as outcomes — "you'll be able to..." —
   before writing any prose. If the request has no clear objective, ask or propose one.
2. Sequence the content using the instructional design foundations (hook, chunk into steps,
   examples, recap, what's next).
3. Write following the style guide: active voice, short sentences, digits for numbers,
   Celonis naming conventions.
4. Apply the inclusion checklist to all examples, names, and characters as you go — not as a
   final pass.
5. For voiceover content, follow the voiceover-specific rules: spell out special characters,
   keep sentences even shorter.

---

## Step 4 — Review existing content

When asked to review or check a draft against "our standards" or "the guidelines":

1. Run through both `celonis_content_style_guide.md` and `instructional_design_foundations.md`
   as a checklist.
2. Flag concrete issues with a short reason each — e.g. "passive voice: 'It is triggered by
   Celonis' → 'Celonis triggers it automatically'".
3. If the content includes quiz or exam questions, also check against
   `question_writing_guide.md` and note any violations.
4. Summarise what's working, what needs fixing, and what's a judgment call.

---

## Step 5 — Hand off to the next step

When the content design is approved or the draft is ready:

- If it needs TI widget formatting (blue boxes, tabs, accordions, TI page structure) → use
  `/write-course-script`
- If it needs assessment questions written or reviewed → use `/write-exam-questions`
- If it's ready for HTML conversion → use `/convert-course-to-html`
