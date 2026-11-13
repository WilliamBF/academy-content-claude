---
name: "design-course-content"
description: "Plan, outline, structure, and review Celonis Academy training content using the team's instructional design foundations and content style guide. Use for: planning a new course, microcourse, video or learning path; brainstorming topics and hooks; defining learning objectives and audience; outlining sections, lessons and pages; sequencing and chunking content; storyboards; drafting rough first-pass content; designing knowledge checks; and reviewing or checking any draft against the style guide, tone of voice, standards or guidelines (active voice, sentence length, numbers, naming, inclusive language). Use at the start of any new content piece, before scripting. For writing the final page copy or script text with widget markup, hand off to write-course-script."
---

# Design Course Content

This skill covers the design and drafting phase of the content pipeline — the work that happens
before scripting. It applies the team's instructional design theory (structure, sequencing,
objectives) and the Celonis content style guide (tone, naming, inclusion) at the same time.

Pair it with `/write-course-script` (TI widget production) and `/write-exam-questions`
(assessment items) once the design is approved.

**Routing:** this skill owns planning, outlining, objectives, sequencing and rough drafts. Once the
structure is settled and the task becomes writing the actual page text or a voiceover script,
switch to `/write-course-script` (see Step 5). If a request mixes both, design first, then continue there.

**Lean mode (optional):** if the instructional designer asks for it, keep output to what the learner
or reviewer will use: no pages or sections added for completeness, no production scaffolding or meta
notes about why a page exists, no review-setup section, no changelogs or terminology tables. Off by default.

---

## Step 1 — Confirm content type and source material

Ask only for what the request does not already tell you:

1. **Content type** — e.g. a microcourse, a video/voiceover script, a full course, a module
   outline, a knowledge check, an exam, or something else. This matters because:
   - Voiceover scripts need shorter sentences and spelled-out special characters
   - Exams have stricter format rules than regular quizzes
   - Course/module outlines need sequencing decisions a single page script doesn't
   - Each asset type has its own structure and length limits: see `reference/asset-types.md`
2. **Source material** — a Google Drive folder, local files, or other docs beyond the bundled
   references. Don't assume based on a past conversation — ask every time.

3. **Metadata and roles** — capture these once, up front, so they are not chased at upload time:
   working title, catalog description, meta description, level, duration, role and feature,
   target persona, owner, SMEs (primary and secondary), peer reviewer, and existing resources to
   reference. Character limits and defaults: `reference/asset-types.md`. Keep titles and
   descriptions keyword-relevant and never padded to hit a limit.

If invoked with no task at all (bare slash command), also ask for the topic:
> "What would you like to create, and what should it cover? What kind of content is it
> (microcourse, video script, full course, exam, etc.)? Do you have a Google Drive folder or
> local files with source material?"

If they provide a Drive folder or local files, read them before drafting.

---

## Step 2 — Load the right reference material

Reference files are bundled with this plugin — read whichever apply to the task:

- `$CONTENT_CREATION_PLUGIN_ROOT/reference/asset-types.md` — structure and length limits per
  asset type. Read this when choosing or checking the content type.
- `$CONTENT_CREATION_PLUGIN_ROOT/reference/instructional_design_foundations.md` — the theory:
  learning needs analysis, outcome-based objectives, content sequencing, Gagne's 9 events,
  the 8-step ID process, evaluation. Read this when planning structure or sequencing.
- `$CONTENT_CREATION_PLUGIN_ROOT/reference/celonis_content_style_guide.md` — the house style:
  tone, active voice, sentence length, number formatting, naming conventions, the inclusion
  checklist, voiceover rules. Read this when writing sentences or reviewing a draft.
- `$CONTENT_CREATION_PLUGIN_ROOT/reference/question_writing_guide.md` — how to write knowledge
  checks and qualification exam questions: Bloom's cognitive levels, MCQ/MRQ format rules,
  distractor writing, what's off-limits in qualification exams. Read this whenever the task
  involves any quiz or exam questions.
- `$CONTENT_CREATION_PLUGIN_ROOT/reference/snippet-cheat-sheet.md` — the full menu of snippet
  tags (callouts, media, interactive, structure and layout, text and code). Read this when
  outlining pages or storyboarding, so each page's format is chosen from the whole set and not
  just blue boxes, tabs and accordions.

These are working copies of live Confluence pages. If a task turns on a detail that seems
outdated or missing, re-fetch the live page rather than trusting the cached copy.

---

## Step 3 — Draft new content

1. Confirm (or help pin down) the learning objective(s) as outcomes — "you'll be able to..." —
   before writing any prose. If the request has no clear objective, ask or propose one.
2. Sequence the content using the instructional design foundations. Include a hook or recap where
   it adds value for the learner, not on every page or lesson.
3. For outlines and storyboards, suggest a page format where the shape of the content calls for
   one, chosen from the snippet cheat sheet and varied across consecutive pages, for example:
   a comparison -> sidetoside; a process or flow -> processsnippet or verticalstepper; parallel
   options -> Tabs; a scannable list -> Accordion; related UI screens -> carousel; a demo ->
   videoembed. Flag where a separate TI page type fits (QuizPage, FlipCardPage, HighlightZonePage),
   at most one knowledge check per lesson. Where a page presents a process, comparison or
   decision, suggest a graphic for it, and show options as cards or a decision tree rather than prose.
   **Video storyboard format:** a two-column table, no scene numbers and no screenshots. Left
   column "On screen": a short text description of the visual, any on-screen text, and what is
   being demonstrated. Right column "Voiceover": the script for that beat. One row per beat, so
   reviewers can comment on the row. Screens and images are captured at production.
4. Courses open with a Welcome page (what the course contains, why take it, the objectives in
   plain words, time, prerequisites) and close with a Congratulations page ("You should now be
   able to...", a docs link, next steps and feedback). Include both by default. Label videos
   inside a course as videos in the outline.
5. Review gate: SME review happens on the storyboard or outline. Once approved, messaging and
   visuals are frozen before production; later edits are minor wording only.
6. Follow `celonis_content_style_guide.md` while drafting (voice, numbers, naming, voiceover rules)
   and apply its inclusion checklist to examples, names and characters as you go, not as a final pass.
7. Name options, paths and routes in plain, descriptive words, never A, B1 or Option 1.

---

## Step 4 — Review existing content

When asked to review or check a draft against "our standards" or "the guidelines":

1. Run through both `celonis_content_style_guide.md` and `instructional_design_foundations.md`
   as a checklist.
2. Flag concrete issues with a short reason each, anchored to the exact text (an anchored comment,
   or an inline tag where comments can't be inserted) — e.g. "passive voice: 'It is triggered by
   Celonis' → 'Celonis triggers it automatically'".
3. If the content includes quiz or exam questions, also check against
   `question_writing_guide.md` and note any violations.
4. Add a brief summary of what needs fixing and what is a judgment call only if the user asks for one.

---

## Step 5 — Hand off to the next step

When the content design is approved or the draft is ready:

- If it needs TI widget formatting (any snippet tag in the cheat sheet, TI page types, page structure) → use
  `/write-course-script`
- If it needs assessment questions written or reviewed → use `/write-exam-questions`
- If it's ready for HTML conversion → use `/convert-course-to-html`
