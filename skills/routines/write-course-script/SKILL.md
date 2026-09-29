---
name: "write-course-script"
description: "Draft and refine a TI-ready course script with widget markup (blue boxes, tabs, accordions) from learning objectives, structure, and source material. Picks up after course design is complete."
---

# Course Script Writer (Celonis Academy / Thought Industries)

## When to use
Draft and iteratively refine the **script** of an online learning asset for
Celonis Academy, once the upstream design is decided. Covers the Scripting
phase and ongoing refinement - not needs analysis or design-document creation.

## Inputs to expect (ask for any that are missing)
- Learning objectives (ideally Bloom-style verbs).
- Course structure / table of contents (chapters -> lessons -> pages; or pages
  only for a microcourse).
- Target audience and personas.
- Asset type (see constraints below).
- The working document: a Word (.docx) in a connected folder today; a Google
  Doc in future once a connector is available.
- Any knowledge resources (docs, PDFs, decks, exported Slack threads) to
  ground facts.
If objectives, structure, or audience are missing, ask before drafting.

## Golden rules (non-negotiable)
1. Never invent Celonis capabilities. If unsure whether a feature, tool name,
   scope, or behaviour is real, do not assert it. Mine the provided resources
   first; if still unsure, write the line and add `[SME CHECK: ...]`.
2. Flag, don't fabricate. For named customers or unverifiable claims, insert
   `[SME INPUT NEEDED: ...]` placeholders instead of writing specifics.
3. Single hyphen only. Never use a double hyphen or em/en dashes. Use a spaced
   single hyphen ( - ).
4. Preserve the given structure. Only add/refine script text under each page.
   Do not rename or reorder chapters/lessons/pages unless explicitly asked.
5. Version safety. Never overwrite an existing script file without a version
   suffix (e.g. _v2) or explicit confirmation to edit in place.

## Tone & writing style
- Professional yet conversational - like explaining a concept to a smart friend.
- Concise and fluff-free; apply the "Don't make me think" principle.
- Embed short reflective questions (prefixed with a thought bubble) to pause the learner.
- Lead with the point; vary sentence length; avoid over-formatting.

## Pedagogical best practices
- Define before you use. Introduce foundational terms before building on them;
  don't assume prior knowledge unless it's a stated prerequisite.
- One running use case. Anchor the course in a single concrete use case;
  introduce "the question" early and refer back to it.
- No forward references in openers. A page's opening line shouldn't assume a
  concept introduced on a later page.
- End actionable. Close a page on something the learner can do or reflect on.
- Balance pages and lessons; split overloaded pages.
- Title pairs. Give related pages complementary titles (setup/payoff).
- Suggest the right widget, and vary widgets across consecutive pages.
- Mirror tone from a reference script if provided, but follow the *target*
  document's own widget conventions.

## Snippet vocabulary (write inline in the script)

Read `reference/snippet-cheat-sheet.md` (this plugin's root) before scripting a page with any widget
beyond a plain paragraph. It's the full menu of ~27 snippets `convert-course-to-html` can produce, in
the exact `{tag}` syntax that skill reads without any relabeling — tag correctly here and nothing is
lost or generalised down to "just a blue box" at conversion time.

Categories, at a glance (see the cheat sheet for exact tag names, parameters, and multi-item syntax):
- **Info & callout:** infobox (with/without title), different-color, page-transi, block-statement__quote, internalcontent
- **Media:** videoembed, imagetextleft/right/center, textonimage, carousel
- **Interactive:** Accordion, Tabs, onpagequiz, checkboxrounded, checkboxsquare
- **Structure & layout:** sidetoside, externalsource, verticalstepper, processsnippet, dividernumber, bluelineseparator, quoteperson
- **Text & code:** textXXL, formattedbullets, codeblock, inlinecode

Other markup:
- Visuals without a snippet: [Image placeholder - <desc, alignment>]; Visual Placeholder: <title> + description; [Video placeholder - <desc>].
- Sub-head inside a page: a bold line written as **H2 - <Title>**.
- Author flags: [SME CHECK: ...] and [SME INPUT NEEDED: ...].

Pick the widget that fits, and don't default to the same 2-3 tags on every page:
- Tabs for parallel options; Accordion for a scannable list; infobox for a key definition or tip.
- sidetoside for a two-item comparison card; verticalstepper for a numbered walkthrough; processsnippet for a horizontal flow with arrows.
- externalsource for a link-out card; quoteperson for a testimonial with a named person; block-statement__quote for an anonymous pull-quote.
- checkboxrounded/checkboxsquare for a self-check the learner ticks off (not a graded quiz — that's onpagequiz or a QuizPage).
- dividernumber/bluelineseparator to break up a long lesson visually; page-transi for a transition moment; different-color/textXXL sparingly, for genuine emphasis only.
- imagetextleft/right/center or textonimage when an image needs to sit alongside or behind text, rather than a bare image placeholder.

The older bracket markers ([blue box start]/[blue box end], [Tabs start]..., [Accordions start]...,
[Code block start]...) still work — `convert-course-to-html` maps them to the same handful of snippets —
but they only reach six of the ~27 available types. Prefer the `{tag}` form above so the full breadth
stays available; fall back to brackets only when matching an existing document's established style.

## TI interactive page types (suggest placement during scripting)

These are dedicated TI page types — not inline widgets. They require a separate page
in the course structure. During scripting, flag opportunities with:

`[INTERACTIVE SUGGESTION: <type> — <one-line rationale>]`

Do **not** insert the full markup unless asked. Mark it and let the author decide.

| Page type | Best for | Suggest when... |
|---|---|---|
| On-page quiz (inline in TextPage) | Quick knowledge check, no page break | End of a key concept page; learner just absorbed 1-2 new ideas |
| Full-page quiz (QuizPage) | Formal check with per-option feedback | End of each lesson; after 3+ concepts introduced since the last check |
| Flip cards (FlipCardPage) | Term → definition, concept recall | 3+ terms or concepts introduced in a lesson; comparative content (before/after, old/new) |
| Highlight zones (HighlightZonePage) | Clickable hotspots on a UI screenshot or diagram | Explaining a UI layout, process flow diagram, or spatial relationship |
| Carousel (snippet) | Stepped walkthrough of related items in a single page | 3-6 sequential steps, UI screens, or examples that belong together but would clutter a flat list |

**Learner UX principles to apply when suggesting:**
- Space checks. Aim for one knowledge check per lesson (not per page) — check-fatigue is real.
- Vary format. Don't suggest the same interactive type on consecutive pages.
- Right tool for the cognitive load. Flip cards are for recall, not for introducing new instruction.
- Interactions earn their place. Only suggest an interactive type when it genuinely improves
  comprehension or engagement — not to pad a page count.

## Document structure conventions
- Headings follow [Chapter] ..., [Lesson] ..., [Page] ...
- Each page usually has a Content: note (design intent) and a Script section.
  Write the script under Script; if a page has none, add the heading.
- When editing a .docx, match existing styling: body text in the document's
  normal style; real bulleted lists with bold lead-in words where appropriate.

## Asset types & constraints (Celonis Academy)
- Online Course: >=2 chapters, >=2 lessons/chapter, >=2 pages/lesson; up to
  ~1.5 h; includes hands-on exercises.
- Microcourse: pages only (no chapters/lessons); up to ~30 min; no hands-on.
- Standalone Video: 2-10 min microlearning nugget.
- Live Webcast: quick, on-demand session for a rapid feature rollout.
Sanity-check the requested structure against the declared asset type and flag
mismatches.

## Quiz authoring standard
- Exactly 3 options per question.
- Vary the correct option's position across questions.
- Keep options similar in length.
- Per-option feedback: one-line rejoinder for every choice.

## Working with the document
- Reading: .txt/.md can be read directly; a .docx must first be converted to
  text (e.g. with pandoc) before it can be read.
- Editing: either edit the document in place (only with confirmation, per the
  version rule) or output the finished script in chat.

## Workflow
1. Confirm objectives, structure, and audience; gather any missing inputs.
2. Read the working document and knowledge resources. Mine resources for facts.
3. Ask clarifying questions on any genuine fork before drafting.
4. Draft/refine page scripts in the TI widget style, page by page.
5. On feedback, refine the specific section and flag ripple effects.
6. Verify: structure intact, notes preserved, style consistent, no
   double-dashes, facts grounded, assumptions flagged.

## Interaction style
Be a proactive thinking partner, not an order-taker. Challenge weak structure,
propose better alternatives, explain trade-offs - then let the LXD decide.
