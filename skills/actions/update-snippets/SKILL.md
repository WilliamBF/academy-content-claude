---
name: update-snippets
description: >-
  Identify which reusable HTML content snippets (accordion, tabs, infobox, carousel, etc.) are used on Celonis Academy / Thought Industries course pages, and detect when a page is running an outdated structural version of a snippet that needs migrating to the current one. Trigger this whenever a course owner or LXD asks things like "which snippets are on this page", "audit this course for outdated widgets", "is this course using the old accordion", "migrate the old [snippet name] in [course]", or "update this page's snippets to the current version". Also trigger proactively (but briefly — a one-line heads-up, not a full report) whenever other work in this session touches a course topic whose raw HTML matches a known legacy snippet signature (per reference/legacy-snippet-blocks.html in WilliamBF/academy-content-claude), even if snippet auditing wasn't the original ask. Also trigger when a course owner asks to add the "embedded" class/treatment to links pointing at docs.celonis.com, or when other work on a course page surfaces a docs.celonis.com link that doesn't already have class="embedded" — flag it in one line and offer to walk through the opt-in flow, but never apply the class without asking first. Do NOT trigger for general course-content editing, writing, or review tasks that don't involve these specific reusable HTML blocks — use write-course-script, review-course, or evaluate-course-for-* for those instead.
---

# Update Snippets

Celonis Academy courses in Thought Industries reuse a fixed library of ~17-27 HTML content blocks ("snippets" — accordion, tabs, infobox, carousel, and so on). TI has no linked/shared component system: every time a snippet is pasted into a course page, it becomes static HTML baked into that topic. When a snippet's structure changes, old copies already living in course pages do **not** update themselves — they silently drift out of date, and nothing in TI tells you where they are.

This skill has three jobs. Two of them — auditing and migrating — are built on two separate sources of ground truth, described just below; there is no local snippet registry, so don't use `snippet-registry/` for this skill even if it exists in the workspace. The third — applying the embedded-docs link treatment, described in its own section further down — works differently: it isn't about detecting an outdated version of anything, it's about asking the course owner whether to opt into a fixed treatment for a specific link pattern. All three jobs are organized below purely for internal structure — never name them to the user (not "Mode 1", "Mode 2", or anything else). Just show them the audit results, walk them through the migration, or run the embedded-docs flow directly, without naming any of it.

## Sources of truth

- **Current version of each snippet** — `reference/html-snippet-blocks.html` in the GitHub repo **WilliamBF/academy-content-claude**. One snippet block per `<!--{name}-->` comment.
- **Legacy/old version(s) of each snippet** — `reference/legacy-snippet-blocks.html` in the same GitHub repo, **WilliamBF/academy-content-claude**.

Both files live in the same repo and are fetched live via the GitHub connector whenever you actually need their content for an audit or migration — don't rely on a cached copy or on structures memorized earlier in a conversation, and don't mirror either file locally. If a fetch fails, say so and stop rather than guessing at structure from memory.

**Don't proactively check whether either file has changed.** Fetching for content is fine (and required) every time you audit or migrate, but skip any extra step that checks the file's `sha` against a prior value or notifies the user about updates — that overhead isn't wanted on every run. Only do that check if the user explicitly asks something like "has the snippet reference changed?" or "check for updates on the snippet files." In that case:
1. Fetch the file fresh via the GitHub connector and note the `sha` it returns.
2. Compare it against the `last_known_sha` you stored last time. Persist this in a fixed file inside the user's connected folder (e.g. `reference/.legacy-snippet-sha.json` at the top level of whatever folder they've connected) rather than a generic "workspace" path — this skill has no bundled storage of its own, and anything written outside a connected folder won't survive to the next session. Create the file if it doesn't exist yet — there's nothing to compare against on a first check.
3. If there's no connected folder available to write to, tell the user plainly that you can't persist this check across sessions and can only tell them whether the file changed since the start of *this* conversation.
4. Tell the user plainly whether it changed, and overwrite the state file with the new `sha` and current timestamp either way, so the next explicit check has an accurate baseline.

Outside of an explicit ask like that, just fetch and use the content — no `sha` comparison, no "still the same" line, no state-file writes.

Not every snippet has a legacy entry — the legacy file only covers snippets that have actually changed structure over time (e.g. accordion, tabs). If a snippet you're looking at appears in the current file but has no corresponding block in the legacy file, treat it as "current-only" — there's no known old version to check against, not evidence that nothing could ever be outdated.

If a snippet you're looking at doesn't match anything in either file, say so plainly rather than guessing — treat it as "unclassified," not as an old version of something else.

## Scoping — which courses to check

Before auditing or migrating, you need to know which course(s) to look at. There are exactly two ways to scope this:

1. **A specific list of courses** the user names or links (by title, slug, or `academy.celonis.com` URL).
2. **A single course**, named or linked the same way.

When first invoked in a conversation (not on every subsequent audit within the same thread), briefly state what you can do — check a named course, or a list of courses, for outdated snippets.

## Reusing already-extracted course content

Audit and migrate both need a course's raw HTML, pulled via `extract-TI-course` or `get-TI-course-structure`. If either of those has already been run for a course earlier in this same conversation, don't call it again for that course — reuse the content you already have instead of re-fetching. This is separate from the GitHub snippet reference files above, which should still always be fetched fresh; it's the course content itself that gets reused here, not the current/legacy snippet definitions.

The one thing to be upfront about: reused content reflects the course as it was at the moment it was pulled, not necessarily as it is right now. If the course owner has edited the page directly in TI since then, that edit won't show up in what you're working from. Mention this once, plainly, before using reused content for a migration specifically (since that's the step that pushes something live) — one line is enough, e.g. "heads up, this is based on what I pulled earlier in this conversation, so anything edited directly in TI since then won't be reflected." This isn't a blocking question — say it and keep going unless the owner asks you to pull fresh instead.

## Mode 1: Audit (read-only, always safe)

Given a course (or a specific topic's raw HTML), identify which snippet(s) are present and whether each instance matches a "current" or "legacy" signature, per the two GitHub reference files above (fetched fresh, per Sources of truth above — no change-detection unless the user explicitly asked for it).

**How to match:** don't rely on exact string equality — course owners write varying content inside the same structural shell. Match on structural fingerprints: the outer wrapper class name(s), the presence/absence of specific child elements (e.g. legacy accordion uses `<input type="checkbox">` + `<label class="accordion-label">`; current uses `<button class="accordion-label2">` + `<em class="icon-navigateright">`), and nesting shape. Two instances of the same snippet type will have different visible text — that's expected and not a mismatch signal. Read the full body of every topic carefully and completely — legacy instances can be buried well below the first screen of content (e.g. a second sidetoside block much further down a long page), so don't stop scanning after finding the first match on a page.

**Output — outdated snippets only:** the point of this report is to tell the course owner what needs to change, so only surface pages that actually contain an outdated/legacy snippet. Present this directly as the result — don't frame it as "Mode 1" or as a named phase.

1. Lead with a one-line header: `Find here the outdated snippets in {Course Title}.`
2. Then a Markdown table (printed in chat, or saved as a file if the course is large enough that a file is more useful to hand off) with exactly two columns:
   - **Page Title** — the topic/page name. Each affected page appears in exactly **one row** — never repeat the same page title across multiple rows.
   - **Snippet** — the legacy pattern(s) found on that page, by name only (e.g. `Legacy tabs`, `Legacy accordion`) — do **not** include the "→ replace with current X" mapping here; that comes later, at migration time, not in this overview table. If a page has more than one outdated snippet, list all of them inside that same row's Snippet cell, one per line (e.g. using a line break within the cell), rather than adding extra rows or separating them with semicolons.
3. If the course has **more than one lesson**, group the table by lesson: add a short heading or divider line naming each lesson before its block of rows, in the order the lessons appear in the course. If the course only has one lesson, skip this grouping entirely — just show the plain table, and don't call out in the response that grouping was skipped or that there's only one lesson; that's an internal formatting decision, not something worth narrating.
4. Omit any page that has no snippets at all, and omit any page where every snippet found is already current — only rows with an actual legacy/outdated match belong in this table. Don't call out which pages were omitted or why (e.g. don't say "page X has no snippet content and is excluded") unless the user specifically asks what happened to a given page — the table itself is the report; silence on everything else is the expected, quiet default. If a page has an unclassified snippet (matches neither current nor legacy), don't put it in this table either — mention it separately as a one-line aside after the table if it's worth flagging (this is the one exception worth narrating, since "unclassified" is actionable information, unlike "nothing here"), but don't count it as "outdated" since there's no confirmed current replacement for it.
5. If nothing outdated is found at all, say that plainly instead of printing an empty table.

**Proactive flags:** if you're doing unrelated work (e.g. reading a course topic for a different task) and its HTML matches a legacy signature, mention it in one sentence at the end of your response — don't derail into a full audit unless the user follows up asking for one.

## Mode 2: Migrate

This is where a real course page's content needs to move from an old snippet structure to the current one. Treat every step here as something a human needs to see before anything touches production — this is the part of the workflow with real stakes (live course pages), so move deliberately even when it's tempting to just push through. Present each step directly to the user as what's happening next — don't frame it as "Mode 2" or as a named phase.

1. **Scope.** Ask (if not already given) for either a list of courses or a single course, per the Scoping section above. Once you have the course(s), scan each one's HTML (via `extract-TI-course` / `get-TI-course-structure`, or reused per the section above where applicable) for the legacy signature of the snippet in question, fetched fresh from GitHub as described above.
2. **Report before acting.** Show the course owner the same Mode 1 audit table (Page Title | Snippet, one row per page, lesson-grouped if applicable, legacy pattern names only — no clean pages listed, no narration about omitted or ungrouped pages).
3. **Ask directly whether to begin.** After the table, ask the LXD plainly whether they want to start updating these snippets now. If they decline, stop here — don't proceed further uninvited.
4. **Work through pages one at a time.** If they say yes, go page by page in the order the pages appear in the course (respecting lesson order), starting with the first page that has an outdated snippet. Fully finish one page (all of its snippets) before moving to the next — don't jump around or batch multiple pages together.
5. **Ask automatic vs. manual, per page.** For each page, ask the LXD whether they'd like the update(s) on that page applied automatically (you push the corrected HTML directly) or manually (you guide them through doing it themselves). Handle all outdated snippets on that page the same way, based on their answer.
6. **Transform, don't retype.** For each matched instance (automatic or manual), extract the actual content (text, image `src`/`alt`, links, headings — whatever the legacy structure holds) and rebuild it inside the current template. Work out the field mapping yourself by comparing the matched legacy block against the current block for that same snippet (both fetched per Sources of truth above) — there are no separate pre-written migration notes to lean on. This has to be real parsing, not a find-and-replace — every instance will have different content sitting inside the same shell. If the mapping between old and new fields is genuinely ambiguous for a given snippet, stop and confirm the mapping with the user before rebuilding, rather than guessing at field correspondence.
7. **Automatic branch.** Present a clear before/after diff for the page's instance(s) first — this is a hard requirement, not a nice-to-have. Only after they approve, push the corrected HTML via `update-TI-content` for that specific topic, and confirm what was changed. If they don't approve, don't write anything — instead, drop into the same guidance the manual branch gives (numbered steps, search anchors, exact code to paste in — see step 8 below), so they still leave the conversation able to make the change themselves.
8. **Manual branch — guide them through it, don't just hand over code.** Assume they're capable but don't over-explain basic concepts unnecessarily; keep the tone plain, not condescending.

   **Decide the format first: full page, or bits of code?** Before writing any guidance, check whether the page is heavily snippet-built. Default to handing over the **entire page's HTML** (current content, with only the outdated snippet(s) swapped to current markup — nothing else changed) instead of isolated find-and-replace snippets whenever any of these are true:
   - the page has **3 or more different snippet types** present (not necessarily all outdated — just present),
   - the page has **3 or more accordion instances**,
   - the page has **2 or more tabs snippets**,
   - any of the outdated snippets is a **process snippet**, **vertical stepper**, or **formatted bullets** (these tend to carry a lot of the page's structure, so partial find-and-replace is riskier).

   Otherwise, default to the bits-of-code approach (steps below). Either way, the user can always ask for the other format explicitly — if they do, follow their preference instead of the default.

   **If full page:**
   1. Pull the topic's current full body HTML.
   2. Rebuild only the outdated snippet(s) in the current template (per step 6) — leave every other line of content (headings, paragraphs, images, links, other snippets, even stray/leftover markup) exactly as it is. Never rewrite or "clean up" unrelated content — the only content allowed to change is the snippet(s) actually being migrated (plus the dead-CSS cleanup below).
   3. Give the guidance as a short numbered list, e.g.:
      1. Open the page in the TI course editor and click the **HTML** button to switch to the raw code view.
      2. Select all existing code on the page and delete it.
      3. Paste in the full replacement code below.
      4. Before saving, skim through and confirm the content still reads correctly — you're replacing the whole page's code, so it's worth a quick check that nothing looks off.
      5. Save/publish the page.
   4. Provide the complete replacement HTML as one block, easy to copy in one piece. Call out plainly that this is the full page, not just the changed section, so they don't paste it in expecting a partial diff.

   **If bits of code:**
   1. Give the guidance as a numbered list of concrete actions, e.g.:
      1. Open the page in the TI course editor and click the **HTML** button to switch to the raw code view.
      2. Use Ctrl+F (or Cmd+F on Mac) to search for [start anchor] — this marks the beginning of the block to replace.
      3. Search for [end anchor] — this marks where the block ends.
      4. Select everything from the start anchor through the end anchor (inclusive) and delete it.
      5. Paste in the new code (provided below).
      6. Save/publish the page.
   2. **Choosing start/end anchors:** prefer a distinctive, human-readable text string near the start and end of the block (a heading, a distinctive sentence) over a raw HTML tag fragment whenever one is available — visible text survives more reliably than exact tag syntax. Only fall back to a tag-level fragment (e.g. `<div class="grid-container_2">`) when there's no useful surrounding text to anchor on.
   3. **Known risk with tag-level anchors:** the extraction API can normalize HTML as it re-serializes it (e.g. turning `<br>` into a self-closing `<br />`, or adjusting quote style) — that normalized form doesn't always match what's actually stored in the TI editor's source. If a tag-level anchor is unavoidable, flag that it isn't guaranteed to match byte-for-byte, and suggest the LXD search loosely (e.g. drop the closing slash if `<br />` isn't found) if the exact string comes up empty, rather than presenting it as certain to match. Whenever a human-readable text anchor is available instead, use that and skip this caveat.
   4. Show the exact new code block to paste in, formatted so it's easy to copy in one piece.

   **In both formats:** if migrating a snippet leaves behind dead CSS that only styled that old snippet's classes (e.g. a `<style>` block for `.blabla2` after a legacy sidetoside is migrated) and nothing else on the page still uses those classes, strip that leftover `<style>` block out as part of the same change — don't leave orphaned CSS behind. If a class is still used elsewhere on the page (e.g. another untouched legacy instance sharing the same class), leave its CSS in place.
9. **Move to the next page.** After finishing the current page (either branch), repeat steps 5-8 for the next page with an outdated snippet, until all pages from the table have been handled or the LXD stops.
10. **Report, don't log.** Summarize what was changed (or handed off) page by page in the chat response, covering only the pages that actually had an outdated snippet — don't recap pages that had nothing to update or that were skipped for having no snippet content; that's noise, not signal. There's no persistent migration log to update — nothing needs to be written back to a registry or repo after the fact.

## Embedded docs links (always opt-in, never automatic)

Course owners can mark a link to Celonis product docs — any URL starting with `https://docs.celonis.com` (the slug after that varies every time) — by adding `class="embedded"` to its `<a>` tag, e.g. `<a class="embedded" href="https://docs.celonis.com/en/...">...</a>`. This isn't a versioned snippet like the ones above, so it's never fetched from either GitHub reference file — it's just a fixed attribute you add to an existing link when the owner wants it.

The key difference from everything else in this skill: applying this is never automatic and never silent. A course owner decides, link by link, whether they want it. Treat every occurrence you find as a question to ask, not a fix to make.

**Finding candidates.** Scan the page's raw HTML for every occurrence of `https://docs.celonis.com`.
- If the link already has `class="embedded"`, mention in one line that the snippet's already applied there (e.g. "the Advanced Topics link already has the embedded treatment") — but don't add it to the candidate list or fold it into the decision questions below; it's just a heads-up, not something to act on.
- If it's a plain `<a href="https://docs.celonis.com/...">...</a>` sitting directly in the page's normal content, it's a straightforward candidate.
- If the URL shows up anywhere else — inside another snippet's markup (a card, a button, etc.), or as the target of something that isn't a plain anchor tag (e.g. a button's `onclick`) — don't fold it silently into the candidate list. Call it out separately, in one plain sentence with no structural jargon (say something like "there's also a docs.celonis.com link used inside a button rather than as a normal link," not "nested in a grid-container_2 card"), and ask — as a clickable yes/no question — whether to include it alongside the others.

**Presenting candidates.** Once you know the final candidate set, show them as a simple list of full URLs — the entire `https://docs.celonis.com/...` string for each one, not just the link's visible text and not a truncated slug, so the owner can tell them apart at a glance. Don't explain your reasoning for why something is or isn't on the list, and don't use words like "candidate" — just the plain list of URLs.

**Deciding.** Ask the owner, as a clickable question, what to do with the list: add the snippet to all of them, don't add it to any, or let them pick specific ones. If they choose to pick specific ones, follow up with a clickable multi-select checklist — one option per link, using its visible text as the label and its full URL as the description — and apply only to what they select.

**Applying.** For each link approved, add `class="embedded"` to that `<a>` tag's existing attributes (`<a class="embedded" href="...">`) and change nothing else about the tag or its content. Show the resulting diff before pushing anything live, and only push via `update-TI-content` after the owner confirms it looks right — same diff-before-push discipline as the automatic branch of Migrate, above.

**Proactive flagging.** If you're doing other work on a course page (an audit, a migration, anything) and spot a `docs.celonis.com` link that doesn't already have `class="embedded"`, mention it in one sentence at the end of your response and ask if they'd like to run through this now — don't derail into the full flow uninvited, same as the proactive-flag pattern in Audit above.

## A note on scale

If a migration scope covers many courses, don't try to hold every instance in your head at once — work course by course, confirm scope per course if the owner wants that granularity (they said this matters to them), and don't let a large batch pressure you into skipping the diff-review step for later instances just because earlier ones went smoothly.
