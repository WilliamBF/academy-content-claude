---
name: accessibility-checker
description: >-
  Audit a Thought Industries (TI) Celonis Academy course, page by page, for accessibility issues against Academy/WCAG 2.2 AA standards — empty tags, stray <br>, leftover <style> blocks, malformed lists, inline styling on images/figures, missing alt text, heading/table/link problems, and outdated snippets — and walk the course owner through fixing each one live. Use this whenever someone asks to "audit a course for accessibility", "check if this course is WCAG compliant", "run an accessibility review on [course]", "is this course accessible", "clean up accessibility issues in [course]", or similar — even if they only mention one specific issue type (e.g. "check for missing alt text" or "check this course's headings"), since that's a subset of this same audit. Also trigger proactively, in one sentence, whenever other work in this session surfaces a course topic containing an empty <p></p>, a bare <br> outside a <p>, a leftover <style> block, or an image without alt text — even if accessibility wasn't the original ask. Do NOT use this for general content/instructional-design review (use evaluate-course-for-id or review-course instead) or for snippet-structure migration alone (use update-snippets) — this skill calls update-snippets itself when it finds an outdated snippet, but isn't a replacement for it.
---

# Accessibility Checker

Celonis Academy courses in Thought Industries need to meet WCAG 2.2 AA. A lot of what breaks accessibility is invisible in the TI editor's preview — an empty `<p></p>`, a `<br>` sitting outside any paragraph, a `<style>` block nobody remembers adding, an image with no alt text — none of it looks wrong until you (or a learner using a screen reader) look at the underlying code. This skill's job is to find that class of problem and fix it together with the course owner, one page at a time.

This is **not** an automated fixer that quietly rewrites a live course. Every fix needs the course owner's sign-off before it happens, because you're working directly on a page that's likely already live or about to go live. Move through this deliberately — the whole point is that a human is walking through their own course with you, not that you're doing it silently in the background and handing them a summary at the end.

**Code, not content.** Everything in this skill is about the underlying HTML/structure — tags, attributes, markup — never the actual wording a learner reads. Never change the visible content of a page (rewording sentences, retitling headings beyond what a tag-level fix requires, altering link text beyond the specific non-descriptive-link fix already covered in Step 2, etc.) without the owner's explicit prior approval for that specific change. Structural/code cleanup (removing empty tags, stripping inline styles, fixing tag nesting) is in scope by default per the approval flow below; rewriting content is not — if a fix would require touching the actual words on the page, stop and call that out as a separate, content-level decision before doing it.

**Keep the language plain.** Course owners aren't all technical, so when describing an issue or a fix, favor plain descriptions over jargon where you can (e.g. "a leftover formatting block that's no longer needed" reads better than diving straight into `<style>` internals for someone non-technical) — you can still name the actual tag/attribute so they can find it, just don't lean on code terminology as the primary explanation. Don't mention this preference to the owner; it's just how you phrase things.

For the reasoning behind each check (why it matters, what "correct" looks like, edge cases), see the **Appendix: Accessibility guidelines reference** at the end of this file — it's a bundled summary of the Academy's Confluence accessibility docs. Read it once at the start of an audit so you have the context ready; you don't need to re-open it for every single page.

## Scoping

Same as scoping a snippet audit: you need either a **single course** or a **specific list of courses**, named or linked by title, slug, or `academy.celonis.com` URL. You have no way to browse the catalog looking for accessibility problems on your own — if the user wants a set of courses checked but hasn't named them, ask for titles/slugs/URLs rather than guessing.

## Step 1: Pull the course and get oriented

Extract the course's structure and full HTML (`get-TI-course-structure` / `extract-TI-course`, same tools the snippet-audit workflow uses). Read every page's full raw HTML carefully before showing anything to the owner — don't stop scanning after the first match, issues can be buried well below the first screen of content. Build a complete map of which pages have which issues (per the checklist in Step 2) before moving on.

**Show a summary table before walking through anything.** Once you know what's on every page, present an overview table so the owner sees the shape of the whole audit up front, not just one page at a time.

- **Section** — only include this column if the course has more than one section; the header is just "Section" (never put the actual section name in the column header — names belong in the cells). If the course only has one section, omit the column entirely.
- **Lesson** — only include this column if the course has more than one lesson, same rule as Section.
- **Page** — always included. One row per page that has at least one issue. If a page has no title, show the literal word "Untitled" — don't substitute a description of what was found there as a stand-in name.
- **Issues found** — the check type(s) found on that page, by name only (e.g. "Empty `<p>`", "Legacy accordion", "Missing alt text (3 images)", "Dead `<style>` blocks (2)"), formatted as an actual list inside the cell (e.g. Markdown line breaks with a leading `-` per item) rather than inlined with semicolons. Don't include fix recommendations here, just what was found; the specifics come up when you actually work through that page.

Order rows by course order (section → lesson → page). **Repeat the Section/Lesson name on every row it applies to — don't leave cells blank to group them.** Blank cells for grouping are fragile: different renderers can misalign columns when cells are left empty, and a shifted column here is a real problem (the owner could misread which page an issue belongs to). Repeating the name plainly on each row is the reliable option, even though it reads as more repetitive.

Omit any page with nothing to flag — don't add a row just to say a page is clean, and don't call out that it was omitted. If nothing at all is found across the whole course, say so plainly instead of printing an empty table.

After the table, give a short heads-up on how you'll proceed: something like "I'll go through these pages one at a time and check with you before changing anything." Then start with the first page (in course order, or wherever the owner asks to jump to) that has at least one issue.

## Step 2: What to look for, per page

Read each page's full raw HTML carefully — don't stop scanning after the first match, issues can be buried well below the first screen of content. For every page, check for:

**Empty `<p></p>` tags.** A paragraph tag with nothing inside it has no value on the front end — it doesn't render anything a learner can see or hear, and leaving it in isn't neutral: it's dead weight that can cause further issues down the line (confusing screen-reader navigation, odd spacing, harder-to-maintain HTML). When you find one, be clear about this rather than soft-pedaling it — something like: "found an empty `<p></p>` on this page — it has no value on the front end and leaving it in can cause further issues, so it's just garbage that should be cleaned up." The fix itself is simple: remove it. Ask before removing, but frame the ask as confirming a straightforward cleanup, not as a judgment call with real trade-offs — there's no legitimate reason to keep a truly empty `<p></p>` around.

**`<br>` tags outside a `<p>`, and stacked `<br>`s inside one.** A `<br>` needs to live inside a paragraph tag, and only **one** `<br>` per `<p>` is compliant — `<p><br></p>` is correct, but a bare `<br>` floating outside any `<p>`, or multiple `<br>`s stacked inside a single `<p>` (e.g. `<p><br><br></p>`), are both non-compliant. This isn't always a straight deletion, though: sometimes the `<br>`(s) are there on purpose, to create visual spacing the course owner wants to keep. So when you find one (or a run of several), give the owner both options rather than assuming removal is the only fix: **remove entirely**, or **make it compliant while keeping the spacing** — for a bare `<br>`, that means wrapping it as `<p><br></p>`; for stacked `<br>`s inside one `<p>`, that means splitting them into that many separate `<p><br></p>` elements in a row (one `<br>` per `<p>`), not leaving them stacked in one paragraph. (If you're not sure whether a given `<br>` is "inside" a `<p>` in the sense that matters — e.g. it's inside a `<p>` but also inside some other wrapping element — use your judgment on what would actually render correctly, but when genuinely ambiguous, ask rather than guess.)

**`<style>` tags.** All styling for Academy courses is centralized in the platform's own stylesheet. Be direct about this with the owner: a `<style>` block baked into a course page is **not required anymore** — the centralized stylesheet already covers it — and it's also a maintenance trap, since it can silently override the central styles in ways nobody intended. There should not be any `<style>` tags left in the course at all. Flag any `<style>` block you find, say plainly that it's no longer needed and must be removed, and confirm before removing. The one exception worth pausing on: if removing a `<style>` block would leave dangling classes that were legitimately serving a purpose the owner still wants (e.g. the class is still applied to visible elements and the centralized stylesheet doesn't cover it), mention that trade-off before removing — but this should be rare, since the whole point is that centralized styling already covers it.

**`dir="ltr"` attributes on `<p>` tags.** Some pages have leftover `dir="ltr"` attributes on paragraph tags (usually a byproduct of pasting content from another editor). This attribute isn't doing anything useful — Academy content is already left-to-right by default — so it's just extra clutter in the code. Treat this the same way as an empty `<p></p>` or a leftover `<style>` block: a straightforward cleanup, not a judgment call. Strip `dir="ltr"` from every `<p>` tag that has it as part of that page's approved fixes, and it's fine to bundle this into the same single cleanup question as the other straightforward, no-trade-off fixes on that page (e.g. "Remove the empty `<p>` tags and leftover `dir=\"ltr\"` attributes found on this page?") rather than asking about it separately.

**Split lists.** Sometimes a course owner builds a 3-item list as three separate `<ul>` blocks (each with one `<li>`) instead of one `<ul>` with three `<li>` children. Visually this can look identical, but it changes how a screen reader announces list length and position ("item 1 of 1" three times instead of "item 1 of 3"). If you spot consecutive single-item lists that look like they were meant to be one list, ask the owner to confirm — it's possible they're separate on purpose (e.g. different list-item styling in between), so don't assume and merge without checking.

**Inline styling on `<figure>` and `<img>`.** These need to inherit centralized styling rather than carry ad hoc `style="..."` attributes, and the same goes for inline `height`/`width` attributes on the `<img>` itself. Always strip inline `style`, `height`, and `width` from `<figure>` and `<img>` tags — and check the wrapping `<p>` too: if an image sits inside a `<p style="...">` (a common pattern for sizing/centering an image), strip the inline styling from that `<p>` as well, not just the image inside it. When you find inline styles/dimensions on any of these, plan to strip them as part of the page's fixes (bundle this with the rest of that page's approved changes rather than asking about each one individually — it's a straightforward cleanup, not a judgment call, so a single mention when you present the page's findings is enough).

**Referring to images with the owner.** Never use an image's `data-image` value (or any other code-only identifier) to tell the owner which image you mean — they have no way to check that against what they see in the editor. Instead, point to the image by its position and visible content: which page section it's in, what comes right before/after it in the text, and a plain description of what the image shows (e.g. "the second image on this page, right after the 'How to keep the health score updated' heading — the Salesforce screenshot showing the Contact tab").

**Missing alt text on images.** For every `<img>` with no `alt` attribute (or an empty one used incorrectly — see below), ask the owner one image at a time — never bundle multiple images into a single decision, even if they look similarly decorative at a glance: is this image **decorative** or **informative**? Give a one-sentence definition of each so the answer is easy to make:
- *Decorative*: it doesn't carry information a learner needs — if you deleted it, nothing important would be lost — so it should have empty alt text and no action is needed.
- *Informative*: it conveys content the learner actually needs (a diagram, a screenshot with meaning, a linked image) — if so, remind the owner they need to add real alt text describing it (max ~2 sentences, no "image of…", not a duplicate of any caption).

  If they say decorative, you're done — empty alt text is correct, move on. If they say informative, don't write the alt text yourself unless they ask you to draft something for them to review — remind them it's needed and let them decide the wording, since you can't reliably judge image content the way a person looking at the actual rendered image can. If they'd like your help drafting it, you're welcome to look at the image and propose text, but flag it clearly as a draft for their review, not a final answer.

**Outdated snippets.** If any snippet on the page matches a legacy structural signature (per the `update-snippets` skill's own reference-fetching process), don't try to fix it here — tell the owner you found an outdated snippet, name which one, and offer to run the `update-snippets` skill right now to fix that specific instance (give them the option to do it immediately, rather than just noting it for later). If there's more than one outdated snippet on the page, or across the pages you're flagging, handle each one as its own decision — don't bundle "found 3 outdated snippets, want to fix all of them?" into a single ask, since the owner might want a different approach for each. If they'd rather come back to it, that's fine — note it and move on, and pick it up as a separate step once the rest of that page's accessibility checks are done.

**Headings.** Headings must follow strict sequential order — h1 → h2 → h3 → h4 → ... — with no level skipped on the way down (h1 straight to h3, h2 straight to h4, h3 straight to h5, and so on are all skips, not just the h1→h4 example). Check for: more than one `<h1>` on the page, no `<h1>` at all, any skipped level anywhere in the page's heading sequence, and any leftover `class="courseTitle"` on a heading or styled text. Flag what you find and what the fix would look like (e.g. "this should be an `<h2>` here, not styled text pretending to be one") and confirm before changing tags — retagging headings can occasionally interact with a page's existing CSS in ways worth a second look together.

- **No `<h1>` at all on the page.** Flag this plainly — every page needs one `<h1>` — and remind the owner of that rule. Give them the choice to add one now or skip it for this page: offer "Add an `<h1>`" (work with them on what the title text should be, based on the page's actual topic) or "Skip for now." Don't assume skipping is wrong; some pages genuinely don't need a title added mid-audit.
- **`<h3>` used directly with no `<h2>` or `<h1>` above it on the page.** This is a skipped-level issue, but call out the two things separately: first, remind the owner a main page title (`<h1>`) is still needed, but make clear that part is optional to fix right now; second, offer to convert the `<h3>`(s) to `<h2>` instead, since that's the more compliant fix for the skipped level on its own (an `<h2>` sitting directly under a missing-but-optional `<h1>` is far less of a problem than a bare `<h3>`). Give them the choice: "Convert `<h3>` to `<h2>`" or "Leave as-is."

**Tables built as images.** You can't inspect an image's visual content directly, so treat this as a question rather than a definitive finding: if a page has an image that looks like it might be standing in for tabular data (filename hints like "table", or surrounding text that describes rows/columns), ask the owner to confirm one way or the other. If it is a table-as-image, point them to the accessible table markup in the **Appendix** at the end of this file and offer to rebuild it in code with them — but tell them plainly to keep the old image/code around until the new table is confirmed correct, and that genuinely complex tables are better routed to Design Epic rather than force-fit into code.

**Non-descriptive or same-tab links.** Flag any `<a>` whose visible text is a generic phrase like "click here", "this", "read more", "learn more", or "here" — these don't tell a screen reader user where the link goes. Suggest more descriptive text based on the link's destination/context and confirm the replacement with the owner rather than substituting it unasked. Also flag links missing `target="_blank"` and offer to add it.

**Video iframe titles.** For any `<iframe>` embedding a Wistia video, check for a `title` attribute. If it's missing, or looks like a placeholder (e.g. "final version 1.0", "videoExport_02"), ask the owner for the actual Wistia video name so the iframe title can match it exactly — you have no way to look up the real Wistia title yourself.

## Step 3: Present findings and get decisions, per page

For each page with issues, lay out what you found in plain language before touching anything — a short list is fine, you don't need a formal table for a single page.

**Get every decision through clickable options, not typed replies.** Use the question tool (`AskUserQuestion`) for each approval instead of asking in a plain sentence and waiting for the owner to type "yes" or "remove it" back — a course owner clicking through a page's worth of decisions is much faster than typing a reply to each one, and it keeps their answer unambiguous. Match the options to the specific approval pattern for that check: "Remove" / "Keep" for empty `<p>`s and `<style>` blocks; "Remove" / "Keep but make compliant" for stray or stacked `<br>`s (removal if it's not doing anything, or — if the owner wants to keep the spacing — wrapping each one in its own `<p><br></p>` rather than leaving multiple `<br>`s stacked in one `<p>`); "Merge into one list" / "Leave as separate lists" for split lists; "Decorative" / "Informative" for missing alt text; "Fix heading tags" / "Leave as-is" for heading issues; "Yes, it's a data table" / "No, just an image" for suspected table-images; "Use suggested text" / "Keep as-is" for non-descriptive links; "Add it" / "Leave as-is" for missing `target="_blank"`.

The tool allows up to 4 questions per call, each with up to 4 options. Use that batching to your advantage for the checks where one answer genuinely covers multiple identical instances — e.g. a handful of equally-dead `<style>` blocks can be one question ("Remove the 3 `<style>` blocks found on this page?") rather than three. But **titles/headings, images, and snippets are the exception — always run those one by one, never grouped into a single decision**, even when they look identical at a glance (two images that look similarly decorative might not both be; two outdated snippet instances might get different treatment). If a page has more than 4 distinct decisions once you've split things out this way, send a second batch of questions rather than cramming everything in — don't skip decisions to fit the limit.

Work through the whole page's list before moving to fixes, so the owner sees the complete picture for that page in one pass rather than piecemeal.

## Step 4: Apply the approved fixes

Once you know what's approved for a page, ask the owner how they want it applied — via the same clickable-options pattern ("Automatic" / "Manual"), and no need to re-ask the explanation behind each option after the first page:

- **Automatically** — explain plainly that you'll make the approved changes and push the corrected HTML directly via `update-TI-content` for that topic, then confirm afterward what changed.
- **Manually** — give clear, concrete guidance: what to search for in the HTML editor, what to delete, and exactly what to paste in its place. Keep it as a short numbered list per fix (open the HTML view → find X → delete/replace with Y → save). If several small fixes land close together in the same page, it's fine to bundle them into one set of instructions rather than repeating the open/search/save cycle for each one individually.

If the page also had an outdated snippet, that piece is handled by `update-snippets` (see above) — don't try to fold snippet migration into this automatic/manual choice, since that skill has its own diff-review step for good reason (snippet rebuilds carry more risk than a tag cleanup).

## Step 5: Next page

Move to the next page with findings, repeat Steps 2–4, until every flagged page in the course has been through this process or the owner wants to stop.

## Step 6: Wrap-up — human review is mandatory

Once all pages are done, summarize what was changed (or handed off for manual editing) page by page — skip pages that had nothing to flag, that's not worth recapping.

Then tell the owner plainly: **this automated pass doesn't complete the accessibility check on its own.** They need to add the course to the [Accessibility Monday board](https://celonis.monday.com/boards/1806234305/views/28431682), because a human review is required to actually finish the accessibility sign-off. They can still submit the course to Localization without Design Epic's approval if they need to move forward on that track, but full compliance isn't reached until that human review happens — make sure this isn't a throwaway line at the end they might skim past; it's the one step in this whole process that isn't optional.

## Appendix: Accessibility guidelines reference

Bundled snapshot of two Confluence pages in the CA space, summarized for use during accessibility audits. This is a snapshot, not a live fetch — if the user asks "has the accessibility guidance changed?" or wants the absolute latest wording, re-fetch these two pages directly rather than trusting this section blindly:

- **Online Training x Accessibility** — https://celonis.atlassian.net/wiki/spaces/CA/pages/70942838/Online+Training+x+Accessibility (page ID 70942838)
- **FAQs Accessibility** — https://celonis.atlassian.net/wiki/spaces/CA/pages/4459560988/FAQs+Accessibility (page ID 4459560988)

Celonis Academy targets **WCAG 2.2 level AA**. This appendix exists to give context and phrasing for the checks the skill performs — it is not itself a checklist to run mechanically; the body of this file defines the actual audit steps.

### Headings

- Screen readers navigate by heading tag, not visual size/weight — a title styled to *look* like an h1 without the actual `<h1>` tag doesn't help anyone using a screen reader.
- Only one `<h1>` per page, and it must be the first heading.
- Main titles should stay within h1–h3 — don't skip levels (no jumping from h1 to h4, or starting a page at h2 then using h4 next).
- Remove any leftover `class="courseTitle"` — it's a legacy pattern, correct heading tags replace it.

### Font size

- TI centralizes text sizing; you normally shouldn't need to touch it. If you do find inconsistent sizes: regular text must be at least 16px, large text at least 24px.

### Links

- Link text must be descriptive on its own — screen reader users can pull up a page's full list of links out of context, so text like "click here", "this", "read more", "let's go" tells them nothing about where it goes. Compare "click here to start the Apps course" vs. "Start the Apps course and learn all about Marketplace."
- Links should open in a new tab (`target="_blank"`) — losing your place in a course to an external link, especially with limited mobility, is disruptive.

### Color

- Don't use color as the only way to distinguish something (e.g., a chart legend, a "this is a link" cue) — colorblind/low-vision users and screen reader users won't perceive it. Pair color with another cue: underline, bold, shape, a text label.
- TI links are already blue + underlined by default, which satisfies this — don't strip the underline.
- Approved brand/support colors if color contrast comes up: `#FFFFFF`, `#000000`, `#0029FF`, `#5CFE50`; highlight text `#0F233E` on background `#E5E9FF`; warnings `#8E0000` on `#FFDDDD`; greys `#767676` / `#E5E5E5`.

### Images and alt text

- Avoid using an image of text as a stand-in for real content — it can't be localized and screen readers can't read it. This doesn't apply to images that combine text with other meaningful visual content (graphs, screenshots, diagrams) — those are fine, just add a description (an accordion works well) below them.
- **Decorative image**: doesn't carry important content, used for layout/decoration, isn't a link. Test: if you deleted it, would anything important be lost? If no, alt text should be left **empty** (not filled with junk text) so screen readers skip it.
- **Informative image**: carries content a learner needs. Needs alt text, max ~2 sentences, describing what the image shows.
- If an image is a link, the alt text must describe where the link goes.
- Never duplicate the caption and the alt text — only add a caption if it says something the alt text doesn't.
- Never start alt text with "image of…" or "screenshot of…" — screen readers already announce it's an image before reading the alt text.
- For very detailed images: put the description in the course text itself if it fits naturally, or add an accordion titled "Description of the image: [title]" right below the image with the detail, and keep the alt text short (e.g. "[brief description]. Detailed description below the image.").
- Set alt text in TI via: click the image → Edit → fill in the **Title** field (that's the alt text).

### Tables

- Tables must be built as real HTML tables, never as images (screen readers can't read table images at all).
- Accessible table shape: `<caption>` describing the table's content, right after `<table>`; headers wrapped in `<thead>` using `<th scope="col">` or `<th scope="row">` (screen reader support is better for `scope="colgroup"` than `scope="rowgroup"`); body content in `<tbody>` using `<td>`.
- If a course owner isn't comfortable editing table HTML themselves, that's a hand-off to Design Epic — this skill shouldn't attempt an invasive table rebuild without the owner's explicit go-ahead, and should preserve the old code until the new version is confirmed correct.

### Snippets

- Old TI snippets predate current accessibility work (responsive sizing, zoom support, contrast). Any legacy snippet found during this audit should be routed to the `update-snippets` skill rather than fixed ad hoc here.
- Of the interactive widgets: "Interactive" hotspots are accessible as long as each box has a real title and nothing in the image is missed by only reading the text, and the order hotspots are added in matches the order a learner should experience them (that's the order a screen reader follows). "Highlight zones" are technically accessible but discouraged (awkward keyboard navigation) — use only if there's no other way to convey the content. "Highlight Zone Challenge" is not accessible at all and shouldn't be used.

### Video

- All videos need closed captions, generated via the Wistia profile page's CC/Transcript tab.
- When a video is embedded via iframe in a text page, the iframe needs a `title` attribute matching the video's actual name in Wistia. If the Wistia name itself is a placeholder like "final version 1.0" or "videoExport_02", that name should be corrected too, so both instances agree.
- Avoid flashing content (more than 3 flashes/second, large area, high contrast, especially red) — seizure risk for photosensitive users.
- Videos without audio/voiceover: figure out whether the video merely repeats text already on the page (add a short note like "this video has no sound — it's a step-by-step on X"), adds moderate new detail on top of things already explained (summarize the steps in a bullet list, optionally inside an accordion), or introduces genuinely new information not covered elsewhere in text (needs a voiceover added).

### Emojis

- Emojis are allowed, but screen readers announce them literally (👉 reads as "right finger") before continuing — use with intent, not as decoration, and don't let them disrupt sentence flow.
- In tables, put an emoji's meaning as visible text *before* the emoji/content in that cell, not after — otherwise assistive tech won't announce the meaning until the entire row/table has already been read.

### Arrows

- Use HTML entities in code rather than literal arrow characters: `&rarr;` for →, `&larr;` for ←.

### Scripting / instructional language

- Don't give instructions that rely on shape, size, color, or screen position ("the blue button", "top right corner", "in the right-hand column"). Name the actual element and, optionally, add a location as a secondary cue for sighted learners: "the Save button", "the Share link button", "the sidebar menu."
- Be specific about what happens ("a new window opens", "a dropdown expands") rather than vague ("click here and there").
- Keep sentences short and punctuation clean — screen readers use punctuation for pacing, and long/complex sentences are harder to follow when listening rather than reading.
- Video voiceover must say everything shown on screen — narrate all steps, describe all elements being clicked, and say the video's title rather than only showing it as on-screen text.

### Publishing step (not part of the HTML audit, but relevant context)

- Once a course is ready (after design review and localization), the **Accessibility Disclaimer** snippet from the Central Asset library should be added at the end of the introduction page — it includes text-to-speech guidance for learners. This is a publishing checklist item, not something this skill inserts unprompted, but worth mentioning if a course owner asks what's left before publishing.
