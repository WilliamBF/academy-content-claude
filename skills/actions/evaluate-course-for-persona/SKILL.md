---
name: "evaluate-course-for-persona"
description: "Evaluate a Celonis Academy course script (Google Doc) or an existing live Academy course against one or more specified personas (customer or partner panorama) to flag what works well, what could be improved, and what's missing for that persona. Produces a suggestions-only Markdown report with prioritized findings — never edits the source directly. Trigger on requests like \"evaluate this script against Project Manager (Partner)\", \"check this course for the AI Lead persona\", \"how well does this serve Executive Sponsor and CoE Lead\"."
---

# Evaluate Course for Persona

Evaluates a Celonis Academy course (new script or existing live course) against one or more named personas, and produces a Markdown review report. This skill only ever *suggests* changes — it never edits the source script or the live course. All suggestions are reviewed and approved (or edited) by the Learning Experience Designer before anything is changed.

**What you can give this skill:** a course script — as a Google Doc link, or an uploaded/downloaded doc file (e.g. `.docx`) — **or** a live Academy course, by just giving its URL (or slug/UUID if you have it). Either way, tell it which persona(s) to check it against.

## When to use

Trigger on requests like: "evaluate this script against Project Manager (Partner)", "check this course for the AI Lead persona", "how well does this serve Executive Sponsor and CoE Lead", "review this against [persona name(s)]".

## Prerequisites this skill depends on

- **Shared persona reference files in Google Drive** — this is the team-wide source of truth so the skill works identically for every LXD, regardless of their local files. Do not look for persona files in the local project folder; always fetch them from Drive using the IDs below via the Google Drive connector (`search_files` with a `parentId` filter, then `read_file_content` on the matched file).

  - Root personas folder: `1Q2YXOyK8MNi-PIytD3k6NU6LapID3PZB` (link: https://drive.google.com/drive/folders/1Q2YXOyK8MNi-PIytD3k6NU6LapID3PZB)
  - Customer personas subfolder: `1AvUgq8Ap3aSb89c1jMx0OBbhOhN-KDYF` — contains one file per role (e.g. `executive-sponsor.md`, `ai-lead.md`, `celonis-coe-lead.md`, `it-lead.md`, `data-analyst.md`, `enterprise-architect.md`, `value-architect.md`, `data-engineer.md`, `project-manager.md`, `celonis-champion.md`, `business-user.md`, `process-lead.md`), plus shared context files `_context.md`, `_prospect-personas.md`, `_dell-case-study.md`, `_job-title-analysis.md`.
  - Partner personas subfolder: `19fw7Da5KrFxP2_YvJqLk7GxiHiGaxNVS` — contains `account-lead.md`, `transformation-lead.md`, `project-manager.md`, `consultant.md`, `partner-exec.md`, `partner-champion.md`, `alliance-manager.md`, plus `_context.md`.

  To load a specific persona: `search_files` with query `title = '<slug>.md' and parentId = '<customer-or-partner-folder-id>'`, then `read_file_content` on the returned file ID. If unsure of the exact slug, search by `title contains '<partial name>'` scoped to the right folder first.

  **Do not load the `_context.md` files as part of a normal evaluation run.** They contain deck-level scaffolding (persona methodology, org-maturity models, customer-journey involvement tables) that doesn't feed the evaluation rubric in Step 4 — loading them would add tokens and a Drive dependency for no benefit to the findings. The durable facts worth knowing from them are captured statically below instead.

  Some persona files are known to be thin or placeholder-only in the source deck (e.g. `partner-champion.md`, `partner-exec.md`, `alliance-manager.md` have little to no real empathy-map content). If a requested persona's file is thin, say so upfront rather than evaluating against invented detail — do not treat this as a skill malfunction, it reflects a genuine gap in Celonis CX's source material.

  **Three customer-side roles have no partner-specific empathy map and should fall back to the customer file when a partner evaluation is requested:** Value Architect, IT Lead, and Data Engineer. The partner deck explicitly notes each of these roles "can also be fulfilled by a partner," and reproduces near-identical empathy-map content rather than a distinct partner version. When the user asks to evaluate one of these three against "(Partner)," use `personas/customer/value-architect.md`, `personas/customer/it-lead.md`, or `personas/customer/data-engineer.md` respectively, and say so explicitly in the report's header note (as already done for Value Architect) rather than reporting no persona file exists.

- For existing/live courses: the `extract-TI-course` skill (or equivalent), used to pull a course's structured content by UUID/slug rather than scraping the site directly.
  - Note: catalog/slug search can be unreliable — the `browse-TI-catalog` script's page-number pagination may return the same results repeatedly. If slug search via `extract-TI-course --slug` fails after searching several pages, try the direct lookup endpoint `GET /incoming/v2/courseGroups/slug/<slug>` to resolve the slug to a courseGroup ID, then `GET /incoming/v2/courseGroups/<id>/courses` to get the course ID, and pass that to `extract-TI-course --course-id`.
  - Requires the user's own Celonis Academy / Thought Industries API credentials (API key + learner email/password) to be set up for `extract-TI-course` to work. If they aren't configured, ask the user for them rather than assuming they exist.
- For new course scripts: a connected Google Drive tool to read Google Doc content, or — if the user has instead uploaded/attached a local file (e.g. `.docx`) — read that file directly (for `.docx`, extract text via `pandoc -t markdown`, per the `docx` skill's guidance).

## Step 1 — Confirm scope

If not already clear from the request, ask the user:
- Which persona(s) to evaluate against, and which panorama each belongs to (customer or partner) — these are separate persona sets with separate access, so never assume.
- The source: a Google Doc link or uploaded doc file (new/in-progress script) or an existing Academy course (name, URL, or UUID/slug).
- Whether this is a single-persona check or a multi-persona check. Multi-persona is fine when the user asks for it explicitly (e.g., "check this against both Project Manager and IT Lead") — in that case produce one report with a clearly separated section per persona, not separate files.

Do not proceed to load content or personas until scope is confirmed — asking a quick clarifying question here is cheaper than re-running the whole evaluation.

If the course's own metadata/tag names a different persona than the one(s) requested, or if you notice the uploaded source contains more than one draft/version concatenated together, flag this to the user explicitly and ask how to proceed rather than silently picking one interpretation.

## Step 2 — Load only the relevant persona file(s) from the shared Drive folder

Fetch the Markdown file(s) for exactly the persona(s) named, from the shared Drive folder IDs listed in Prerequisites above — e.g. the `project-manager.md` file inside the customer or partner subfolder as appropriate. Do not fetch the entire persona deck or unrelated personas by default; this keeps the evaluation focused and token-efficient.

Only fetch an *additional*, non-requested persona file if the user's request is explicitly about a boundary question (e.g., "why isn't this also relevant for X") — otherwise stick strictly to what was asked.

## Step 3 — Retrieve the course content

- **New course script, Google Doc:** read the doc's content via the Drive connector.
- **New course script, uploaded/local file (e.g. `.docx`):** read it directly from disk — for `.docx`, extract with `pandoc -t markdown` (see the `docx` skill for details) rather than trying to parse the binary format manually.
- **Existing live course:** use the `extract-TI-course` skill (by UUID/slug — a full Academy URL works too, the slug can be extracted from it) to get structured Markdown of the course's sections/lessons/topics. Ask the user for the course identifier if not provided. Avoid ad-hoc scraping of the Academy site when a structured extraction path already exists. See the pagination workaround note in Prerequisites if slug search fails.

## Step 4 — Evaluate against the persona rubric

For each requested persona, judge the course content against these dimensions, all drawn directly from that persona's empathy-map fields:

1. **Jobs-to-be-done / responsibilities fit** — does the content address what this persona actually does day-to-day, or does it drift into a different role's territory?
2. **Expectations & frustrations** — does the content proactively meet what this persona explicitly *expects*, and does it address (or at least not ignore/contradict) what they say they get *frustrated with*?
3. **Seniority & tone fit** — is the depth and tone appropriate given the persona's Example Role and typical job titles (e.g., an Executive Sponsor persona shouldn't get a hands-on technical walkthrough; a Data Engineer persona might expect exactly that)?
4. **Prior-knowledge assumptions** — cross-check against the persona's "Academy Training" / "My Interactions With Celonis" fields. Flag content that wrongly assumes training this persona hasn't typically had, or that redundantly re-teaches something they've already covered elsewhere.

This is a v1, persona-fit-only rubric. It does not check cross-module structural/prerequisite ordering (e.g., whether a concept is used before it's taught) — that's an explicitly deferred v2 scope, not part of this skill yet.

## Step 5 — Categorize, prioritize, and cite every finding

For each finding:
- Categorize as **Works Well**, **Could Be Improved**, or **Missing**.
- For Could Be Improved and Missing items, assign a **priority** — High / Medium / Low — based on how directly it affects whether this persona gets value from the course (e.g., a tone mismatch that would alienate an Executive Sponsor is High; a minor missed opportunity to reference a frustration point is Low). Sort each persona's Could Be Improved and Missing lists by priority, High first.
- Cite the exact quote and its location (section/module/slide/heading) so the LXD can find it without searching.
- For Could Be Improved and Missing items, include a concrete suggested revision — clearly labeled as a suggestion only.
- Give every finding a short, bold title (a few words) before the fuller explanation, so the report is scannable rather than a wall of text per bullet.

Occasionally a finding isn't really a content gap but a structural/tagging question (e.g., "this course's own training-path listing doesn't match what this persona's file says they're expected to take"). Flag these as a distinct **⚠️ Tagging note** type rather than forcing them into Works Well/Could Be Improved/Missing — they need a different kind of follow-up (confirming with CX/persona owners) than a content edit.

Do not silently skip categories that have no findings — state "no issues found" for a persona/category rather than omitting it, so it's clear the check actually ran.

### Formatting conventions (use these consistently)

- **No personal pronouns for the persona.** Never refer to the persona as "she/he/they/her/his/their" anywhere in the report — always use "the persona" or the role name instead (e.g. "the Project Manager," "the Value Architect"). Reports get skimmed out of order — a reader may jump straight to the "At a glance" table or a specific finding and skip the intro paragraph where the persona's name/pronoun would have been established. A pronoun with no nearby antecedent reads as confusing ("who is 'she'?"). This applies everywhere in the report, not just the first mention in a section — every sentence should be understandable in isolation.
- **Priority emoji** (Could Be Improved / Missing only): 🔴 High, 🟡 Medium, 🟢 Low. Markdown has no native color support, so these emoji stand in for a traffic-light system. Never apply priority emoji to Works Well items (they have no priority) or to Tagging notes (they aren't prioritized the same way — use "—" in the priority column instead).
- **Category emoji**: ✅ Works Well, ✍️ Could Be Improved, 🚨 Missing, ⚠️ Tagging note. Use these on the "At a glance" table's Category column and on each `###` section heading. Do not repeat the category emoji on every individual bullet within a section — the section heading already carries it, so repeating it would clutter each line. The one exception is a ⚠️ Tagging note bullet, which keeps its own ⚠️ prefix even outside the table, since it's flagging a different *kind* of finding than its surrounding section.

## Step 6 — Save the report

Save the report as Markdown in a `reviews/` subfolder of the current project (create it if it doesn't exist). Use the naming convention `<course-name>_<persona-slug(s)>_review_<YYYY-MM-DD>.md`. For multi-persona runs, join persona slugs with a hyphen in the filename and use one section per persona inside the file.

Report structure per persona:
```
## [Persona name] ([panorama])

### At a glance

| # | Finding | Category | Priority |
|---|---|---|---|
| 1 | [short finding title] | ✅ Works Well | — |
| 2 | [short finding title] | ✍️ Could Be Improved | 🟡 Medium |
| 3 | [short finding title] | 🚨 Missing | 🔴 High |
| 4 | [short finding title] | ⚠️ Tagging note | — |

### ✅ Works Well
- **[Short title]** — [full finding text, with quote + location — refer to the persona by role name, not a pronoun]

### ✍️ Could Be Improved (by priority)
- 🔴 **High** — **[Short title]** — "[quote]" ([location]) — Suggestion: ...

### 🚨 Missing (by priority)
- 🟡 **Medium** — **[Short title]** — [what's missing, why it matters for this persona] — Suggestion: ...

(If applicable) include a ⚠️ Tagging note bullet within whichever section it's most related to, e.g.:
- ⚠️ **Tagging note (not a content gap)** — **[Short title]** — [explanation of the structural/tagging mismatch]
```

Start each report with a short header block: source file/course name and version note (flagging if multiple drafts were concatenated and which one was evaluated), which persona(s) were evaluated and from which panorama, and any tagging discrepancies noted in Step 1.

Close the report with a brief "Suggested next step" section if the findings point toward a decision beyond individual content edits (e.g., reconsidering whether the persona tag itself is right).

## Step 7 — Hand off for human review

Present the report to the user, but never treat the chat preview as the deliverable. When summarizing the report back in chat:
- Present only a short excerpt (e.g. Works Well/Could Be Improved/Missing highlights), not the full findings — the full report belongs in the saved file, not duplicated in chat.
- Every single time, say explicitly and unmissably that this is a partial summary and the full report — with every finding, quote, location, and suggestion — is in the saved file. Do not rely on a subtle link alone; state it in words, e.g. "This is a condensed preview — the saved report has the complete list of findings with quotes and locations." Put this sentence immediately before or after the link, not buried in a closing paragraph, since users have been observed to treat the chat preview as if it were the entire report and miss the link entirely.
- Always give a direct link/path to the saved file so the user can open it in one click.

Do not edit the original script or push any change to the live course. If the user asks to apply specific suggestions, treat that as a distinct, explicit follow-up action — confirm exactly which items to apply before touching the source.

## Known limitations (be upfront about these)

- Persona-fit only — no structural/prerequisite/knowledge-graph checking yet.
- Quality depends entirely on the underlying persona files being complete; some personas in the source decks are thin or placeholder-only (see Prerequisites), and the skill should say so rather than compensate with invented detail.
- Live-course evaluation depends on the user's own Academy/TI API credentials being set up for `extract-TI-course` — this skill does not access Academy course pages directly.
- The shared Drive folder is the single source of truth for persona data across the whole LXD team. If the underlying persona decks are revised, update the files in that Drive folder (not a local copy) so every colleague's runs stay in sync.

