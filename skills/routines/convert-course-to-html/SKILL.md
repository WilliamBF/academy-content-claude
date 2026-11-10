---
name: "convert-course-to-html"
description: "Transform a course .md draft into structured, TI-ready HTML using the plugin's snippet block library. Handles image placeholders and the CDN upload workflow."
---

# Course Google Doc -> HTML Transformer

You are a **learning experience designer**. Your job is to fetch a course Google Doc, save it as a `.md` draft, then transform its content into structured TI-ready HTML using the project's HTML snippet block library.

---

## Step 0 — Fetch the Google Doc and save the .md draft

Ask the user for the Google Doc URL if not already provided.

1. Use the Google Drive MCP (`readGoogleDoc` with `format: "markdown"`) to fetch the document content.
2. Identify the course folder under `courses/` — ask the user if ambiguous.
3. Write the full markdown content to `courses/<course-name>/02_Drafts/<course-name>.md`, overwriting any previous draft.
4. Confirm to the user that the draft has been saved, then proceed directly to Step 1.

The `.md` file is a pipeline artifact — it is never manually maintained. Always regenerate from the Doc.

---

## Step 1 — Locate the reference file

Read `reference/html-snippet-blocks.html` (in this plugin's root directory) in full before generating any HTML. This is the authoritative source for all snippet structures.

Also read `reference/snippet-nesting.md` before converting any draft that contains a `{/tag}` close tag (see "Nested snippets" in Step 4).

`reference/snippet-cheat-sheet.md` is the authoring-side counterpart — the tag names in Step 4's mapping tables below must stay in sync with it. If an author's `.md` draft uses a `{tag}` from the cheat sheet that isn't in this skill's tables, treat that as a bug to flag (both files should always list the same snippet set), not as an unrecognised tag.

---

## Step 2 — Detect the document style

Course `.md` files come in two styles. Identify which you're working with before proceeding.

### Style A: Clean markdown (Course Structure style)
- Uses standard `##` and `###` headings for structure
- May include `{snippetTag}` lines added by the instructional designer

### Style B: Script/prose format (Microcourse script style)
- Starts with a metadata block (asset type, links, author names, duration) — **skip this block entirely**
- Uses `### H1: Title` to mark each **topic page**
- Uses `**H2 - Title**` for sub-headings within a page
- Contains inline formatting markers:
  - `[sb]...[eb]` -> `<strong>...</strong>`
  - `[si]...[ei]` -> `<em>...</em>`
  - `[start inline code]...[end inline code]` -> `<code>...</code>`
  - `[start code]...[end code]` or fenced blocks -> `<div class="code-block"><pre><code>...</code></pre></div>`
- Contains structural prose markers:
  - `[Blue box start]` / `[Blue box end]` -> `{infobox}` snippet
  - `[Accordion start]` / `[Accordion end]` -> `{Accordion}` snippet
  - `[Horizontal line]` / `[Horizontal rule]` -> `<hr>`
  - `[N tabs element...]` -> `{Tabs}` snippet
  - `[Insert ...]` -> image placeholder (see Step 3)
  - `[code block start]` / `[code block end]` -> `<div class="code-block"><pre><code>...</code></pre></div>`
- Contains author flags (`[SME CHECK: ...]`, `[SME INPUT NEEDED: ...]`, `[LINK NEEDED: ...]`, `[INTERACTIVE SUGGESTION: ...]`). These are not learner content: never output them as visible text. Convert each to `<!-- TODO: ... -->` so it appears in the TODO list of the final report.

---

## Step 3 — Images: audit, download, and placeholder

### A. Already on the Celonis CDN
URLs matching `d3i9g4671ronu3.cloudfront.net/course-uploads/...` — carry over as-is.

### B. Hosted on Google Drive or other external URLs
1. Download to `04_Assets/` via bash (`curl -L "URL" -o "04_Assets/filename.ext"`)
2. Insert the placeholder (alt text is filled in by the alt text pass below):
   ```html
   <!-- IMAGE: 04_Assets/filename.ext — needs TI CDN upload before publishing -->
   <p><img src="PENDING_CDN_UPLOAD" alt="" data-local="04_Assets/filename.ext"></p>
   ```
   If the script marks the image as a link, wrap it in `<a href="..." target="_blank" rel="noopener noreferrer">`.

### C. Local files already in `04_Assets/`
If the source document references a local image file that already exists in `04_Assets/`, insert the same placeholder format as in B.

### D. Screenshot/diagram placeholders (no image file exists yet)
```html
<p><em>[Image placeholder: description]</em></p>
```
Keep the script's `purpose:` tag, if any, as a comment so the alt text pass can use it, and add a provisional alt comment so it can be revisited once the image exists:
```html
<!-- ALT TEXT WHEN IMAGE IS ADDED: "what this screenshot shows" -->
```

### E. Animated GIF warning
If the file or context suggests an animated GIF, flag it with a comment (the alt text pass will also queue it for a human check).

### F. Alt text pass (automatic — do not wait to be asked)
After all `<img>` tags are in place and before the image upload workflow below, run the `write-alt-text` skill's process (rules: `reference/alt-text-guidelines.md`) over **every** image in the converted pages, using what you already hold: the script text before/after each image, captions, `<a>` wrappers, and the image file itself (viewed with the Read tool; CDN images are downloaded first).

- Confident cases are written straight into the HTML (`alt="..."` or `alt=""`), with no question to the designer.
- Uncertain cases get a best-guess `alt` plus an `<!-- ALT CHECK -->` marker and are asked about together, in **one** batched question round at the end of the run, then the markers are removed.
- `03_HTML/alt-text-log.md` is created or updated with every alt text (page, image, alt, decision) for the Localization team.
- Mention the outcome in your end-of-run summary in one line (e.g. "Alt text: 14 handled automatically, 2 confirmed with you; log in `03_HTML/alt-text-log.md`; please review the wording").

### Post-generation: image upload workflow

After HTML generation, images need to reach the TI CDN before `PENDING_CDN_UPLOAD` placeholders can be patched. There are two ways to do this — **check which is available before picking one**:

**Path A — Playwright MCP (preferred).** Check whether Playwright MCP browser tools (`browser_navigate`, `browser_run_code_unsafe`, `browser_file_upload`, etc.) are present in the current toolset. If so, follow `reference/playwright-mcp-image-upload.md` in full. Summary: the user logs in manually with their own account (no stored credentials; if the "You are currently a learner." banner appears, click "Return to Management"), Claude creates a new Text page in the dedicated upload course, batch-uploads images via `setInputFiles`, writes `cdn_map.json` incrementally, verifies every filename mapped, and saves the page.

**Path B — Python script (fallback).** Use this only when Playwright MCP tools aren't available, or the user doesn't want to set up Node.js/`.mcp.json` right now. Requires `TI_LEARNER_EMAIL`/`TI_LEARNER_PASSWORD` set in `secrets.env` and a local Playwright install (`pip install playwright && playwright install chromium`):
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/image_uploader.py" <images_folder> --output cdn_map.json
```

Either path produces the same `cdn_map.json` shape, so the patch step is identical either way:
```bash
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/routines/convert-course-to-html/patch_cdn_urls.py" <html_file> <cdn_map.json>
```

> **Cowork users:** neither path works in Cowork. The script needs a local Playwright install; the MCP path needs a local session with Node.js and `.mcp.json` configured. Switch to Claude Code desktop/CLI for this step.

---

## Step 4 — Snippet tagging system and deviation handling

Instructional designers tag sections with `{snippetname}` on its own line. The tag applies until the next heading or tag.

### Deviation resolution table

| Author writes | Resolve to |
|---|---|
| `{note}`, `{tip}`, `{blue box}`, `{callout}`, `{hint}` | `{infobox}` |
| `{warning}`, `{caution}`, `{alert}` | `{infobox}` |
| `{video}`, `{wistia}` | `{videoembed}` |
| `{dropdown}`, `{expand}`, `{collapsible}` | `{Accordion}` |
| `{tab}`, `{tabbed}` | `{Tabs}` |
| `{quiz}`, `{knowledge check}`, `{question}` | `{onpagequiz}` |
| `{external}`, `{link card}`, `{resource}` | `{externalsource}` |
| `{steps}`, `{stepper}` | `{verticalstepper}` |
| `{process}`, `{flow}` | `{processsnippet}` |
| `{divider}`, `{numbered section}` | `{dividernumber}` |
| `{separator}`, `{hr}`, `{line}` | `{bluelineseparator}` |
| `{highlight}`, `{banner}` | `{page-transi}` |
| `{quote}` (with person) | `{quoteperson}` |
| `{quote}` (no person) | `{block-statement__quote}` |
| `{image left}`, `{image right}`, `{image center}` | `{imagetextleft/right/center}` |
| `{image overlay}`, `{image with text}` | `{textonimage}` |
| `{slideshow}`, `{gallery}` | `{carousel}` |
| `{checkbox}`, `{checklist}` | `{checkboxsquare}` |
| `{radio}`, `{options}` | `{checkboxrounded}` |
| `{code}` | `{codeblock}` |
| `{numbered list}`, `{ordered list}` | `{formattedbullets}` |
| `{big text}`, `{large text}`, `{display text}` | `{textXXL}` |
| `{colored block}`, `{colored background}` | `{different-color}` |
| `{internal}`, `{internal only}`, `{staff only}` | `{internalcontent}` |

For anything not in this table, use context to make a judgment call. Never silently drop content.

### Available tags and snippet mappings

| Tag | Snippet |
|---|---|
| `{sidetoside}` | Two-column title + description layout |
| `{externalsource}` | External link card |
| `{videoembed}` | Wistia video embed |
| `{infobox}` | Highlighted note/tip box (no title) |
| `{infobox with title}` | Highlighted note/tip box with title header |
| `{imagetextleft}` | Image floated left |
| `{imagetextright}` | Image floated right |
| `{imagetextcenter}` | Centered image |
| `{textonimage}` | Full-width image with text overlay (requires `full` class) |
| `{Accordion}` | Expandable accordion items |
| `{Tabs}` | Tabbed content panels |
| `{onpagequiz}` | Multiple-choice question |
| `{checkboxrounded}` | Radio-button list |
| `{checkboxsquare}` | Checkbox list |
| `{codeblock}` | Formatted code block |
| `{inlinecode}` | Inline code span |
| `{formattedbullets}` | Styled numbered list |
| `{verticalstepper}` | Vertical step progress list |
| `{processsnippet}` | Horizontal process/flow cards with arrows |
| `{dividernumber}` | Numbered divider sections |
| `{bluelineseparator}` | Horizontal blue line separator |
| `{page-transi}` | Page transition / highlight bar |
| `{block-statement__quote}` | Large quote/highlight block |
| `{quoteperson}` | Quote with person image and citation |
| `{carousel}` | Image carousel with captions |
| `{different-color}` | Coloured background text block |
| `{textXXL}` | Oversized display text |
| `{internalcontent}` | "FOR INTERNAL AUDIENCE ONLY" disclaimer banner |

### Nested snippets (`{tag}` ... `{/tag}`)

A tag with a matching `{/tag}` close tag is a **container**; the snippets between the two tags are its **children**. Tags with no close tag behave exactly as before (applies until the next heading or tag). Full syntax, slots and support matrix: `reference/snippet-nesting.md` — that file is authoritative; the summary below is how to act on it.

**Parsing**
1. Match each `{/tag}` to the nearest unclosed opening tag of the same name. A child with no close tag ends at the next tag, bold tab/accordion title or the parent's close tag.
2. Resolve deviations (table above) on both opening and closing tags, e.g. `{/note}` closes `{infobox}`.
3. `{Tabs}`: each bold line inside starts a tab; children belong to the tab above them. `{Accordion}`: each item holds its own children; `{/Accordion}` ends the group. Consecutive flat `{Accordion}` items still merge into one wrapper.
4. **Backward compatibility:** a tag is a container only if a matching `{/tag}` exists. Existing scripts without any close tags (flat `{infobox}`, `{Tabs}`, `{Accordion}`, `{onpagequiz}`, …) convert exactly as before; never treat a missing close tag as an error or a TODO. Only a `{/tag}` with no opener is a TODO: emit `<!-- TODO: unmatched {/tag} -->` and render flat. Never drop content.

**Rendering**
1. Build the parent from the literal markup in `reference/html-snippet-blocks.html`, then build each child from its own reference markup and place it **inside the parent's content slot**, in order (slot table in `reference/snippet-nesting.md`). Add no extra wrapper divs and no extra classes.
2. Plain text inside a container becomes a normal `<p>` in the slot.
3. For `{different-color}`, the container is `<div class="different-color">…</div>`; an optional bold first line is a `<p><strong>` title, children follow in order.
4. Use **unique ids per page** for id-bearing children (`#result` stays as in the reference quiz markup, but `r1..r8`/`c1..c8` and carousel ids must not repeat on one page; rename with a topic-specific suffix if needed, keeping `for`/`aria-controls` in sync).
5. No headings inside a slot (convert any heading to a bold paragraph); the page keeps its single `<h1>`.
6. Every `<img>` inside a slot still goes through Step 3 (CDN placeholder + alt text pass).

**Guardrails — render flat and report, never fail**
Render the children **after** the parent as siblings (flattened) and list the case under "Nesting flags" in the Step 8 report when:
- the combination is marked **Avoid** or **Untested** in the matrix (notably `{onpagequiz}` containing `{Accordion}`, `{infobox}` containing `{formattedbullets}`),
- nesting is deeper than two levels,
- Accordion is inside Accordion, or Tabs inside Tabs,
- a leaf snippet (anything not a container in the slot table) is given children.

Tell the user when flattening happens and suggest the verified alternative (e.g. `{different-color}` instead of `{infobox}` around a list; `{Accordion}` after the quiz, not inside it).

---

## Step 5 — Accessibility requirements (WCAG 2.2 AA)

Non-negotiable rules for every topic page:

- **One `<h1>` per page**, must be first heading. Sequential heading levels. Max depth `<h3>`.
- Every `<img>` has `alt`, resolved by the alt text pass (Step 3F) per `reference/alt-text-guidelines.md`: informative = at most two sentences, no "image of"; decorative or covered by adjacent text = `alt=""`; linked image = describes the destination. No `<!-- ALT CHECK -->` markers left, and `alt-text-log.md` written.
- Link text must be descriptive. All links: `target="_blank" rel="noopener noreferrer"`.
- No inline colour styles — use approved brand colours only if strictly necessary.
- Accordion: `aria-expanded="false"`, `aria-controls` on triggers.
- Tabs: `role="tablist"`, `role="tab"`, `role="tabpanel"` with `aria-selected`.
- Nested snippets: no duplicate `id` values on a page; no heading elements inside a tab panel, accordion body or container slot.
- Every `<iframe>` must have a `title` attribute.
- Tables: `<th scope="col/row">`. Include `<caption>` or `aria-label`.

---

## Step 6 — Transform the content

### General rules
- **Do not rewrite or change the original words.** Preserve the author's exact language.
- Return clean, valid HTML — no markdown syntax, no code fences wrapping output.
- **Never output `<p><br></p>` or `<p></p>` spacer tags.**

### Standard markdown -> HTML conversions
`# Heading` -> `<h1>`, `## Heading` -> `<h2>`, `### Heading` -> `<h3>`, etc.

### Style B structural rules
- Metadata block before first `### H1:` is skipped entirely.
- `### H1: Title` -> new topic page with `<h1>Title</h1>`.
- `**H2 - Title**` -> `<h2>Title</h2>`.
- Consecutive accordion blocks within one page -> single accordion wrapper.

### Snippet-specific notes
- **videoembed** — `width="100%" height="400"`, include `title` attribute.
- **externalsource** — `<p class="extSource-title">` (not `<h4>`).
- **textonimage** — outer div must include `full` class.
- **Accordion** — `accordion-wrapper2` / `accordion-label2` pattern.
- **Tabs** — `snippet--tabs-wrapper` ARIA button pattern.
- **codeblock** — `<div class="code-block"><pre><code>...</code></pre></div>`.

---

## Step 7 — Write the HTML output file

Write to `courses/<course-name>/03_HTML/<course-name>.html`. Separate topic pages with:
```html
<!-- TOPIC: Section Title > Lesson Title > Topic Title -->
```

---

## Step 8 — Post-generation report

Print:
- Topics generated: N
- Snippets used: type and count
- Nested combinations used: parent > child and count (e.g. "Tabs > infobox x2")
- Nesting flags: any combination rendered flat (Avoid / Untested / deeper than two levels / unmatched close tag), with the suggested alternative
- Images requiring CDN upload: filenames in `04_Assets/`
- Possible animated GIFs: flagged images
- Judgment calls: deviation resolutions
- TODOs: any `<!-- TODO -->` comments
