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

---

## Step 3 — Images: audit, download, and placeholder

### A. Already on the Celonis CDN
URLs matching `d3i9g4671ronu3.cloudfront.net/course-uploads/...` — carry over as-is.

### B. Hosted on Google Drive or other external URLs
1. Download to `04_Assets/` via bash (`curl -L "URL" -o "04_Assets/filename.ext"`)
2. **Generate alt text automatically**: use the Read tool to view the downloaded image file, then write a concise, descriptive alt text (1–2 sentences, describe what the image shows — not "image of..."). If the image is purely decorative, use `alt=""`.
3. Insert placeholder with the generated alt text:
   ```html
   <!-- IMAGE: 04_Assets/filename.ext — needs TI CDN upload before publishing -->
   <p><img src="PENDING_CDN_UPLOAD" alt="<generated alt text>" data-local="04_Assets/filename.ext"></p>
   ```

### C. Local files already in `04_Assets/`
If the source document references a local image file that already exists in `04_Assets/`:
1. **Read the image** with the Read tool and generate alt text as in B above.
2. Insert the same placeholder format.

### D. Screenshot/diagram placeholders (no image file exists yet)
Derive the alt text from the surrounding script context (what the screenshot is meant to show):
```html
<p><em>[Image placeholder: description]</em></p>
```
Also add the alt text as a comment so it can be filled in when the image is ready:
```html
<!-- ALT TEXT WHEN IMAGE IS ADDED: "what this screenshot shows" -->
```

### E. Animated GIF warning
If alt text or context suggests an animated GIF, flag it with a comment.

### Post-generation: image upload workflow
After HTML generation, run these two co-located scripts in order:
```bash
python "$CLAUDE_PLUGIN_ROOT/skills/routines/convert-course-to-html/image_uploader.py" <images_folder> --output cdn_map.json
python "$CLAUDE_PLUGIN_ROOT/skills/routines/convert-course-to-html/patch_cdn_urls.py" <html_file> <cdn_map.json>
```

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

---

## Step 5 — Accessibility requirements (WCAG 2.2 AA)

Non-negotiable rules for every topic page:

- **One `<h1>` per page**, must be first heading. Sequential heading levels. Max depth `<h3>`.
- Every `<img>` has `alt`. Informational: concise description. Decorative: `alt=""`.
- Link text must be descriptive. All links: `target="_blank" rel="noopener noreferrer"`.
- No inline colour styles — use approved brand colours only if strictly necessary.
- Accordion: `aria-expanded="false"`, `aria-controls` on triggers.
- Tabs: `role="tablist"`, `role="tab"`, `role="tabpanel"` with `aria-selected`.
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
- Images requiring CDN upload: filenames in `04_Assets/`
- Possible animated GIFs: flagged images
- Judgment calls: deviation resolutions
- TODOs: any `<!-- TODO -->` comments
