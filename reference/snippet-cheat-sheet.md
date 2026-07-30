# Snippet Authoring Cheat Sheet

When writing a course in Google Docs, use the tags below to mark which HTML snippet each section should become. Claude reads the tag and maps it to the correct block — so the closer you follow this, the less cleanup is needed after conversion.

---

## How to tag a section

Put the tag on its **own line**, directly above the content it applies to. Nothing else on that line.

```
{infobox}
Make sure you've completed the prerequisites before starting this module.
```

Tags are stripped from the HTML output — they're for authoring only. Untagged sections become plain headings and paragraphs.

---

## All available tags

### Info & callout boxes

| Tag | What it produces |
|---|---|
| `{infobox}` | Blue info box, no title |
| `{infobox with title}` | Blue info box with a bold title line |
| `{different-color}` | Coloured background block for emphasis |
| `{page-transi}` | Bold transition/highlight bar |
| `{block-statement__quote}` | Large standalone quote or pull-out statement |

### Media

| Tag | What it produces |
|---|---|
| `{videoembed}` | Wistia video player |
| `{imagetextleft}` | Image floated left, text alongside |
| `{imagetextright}` | Image floated right, text alongside |
| `{imagetextcenter}` | Centered image |
| `{textonimage}` | Full-width image with text overlaid on top |
| `{carousel}` | Scrollable image carousel with captions |

### Interactive

| Tag | What it produces |
|---|---|
| `{Accordion}` | Expandable accordion items |
| `{Tabs}` | Tabbed content panels |
| `{onpagequiz}` | Multiple-choice knowledge check |
| `{checkboxrounded}` | Radio-button style checklist |
| `{checkboxsquare}` | Square checkbox checklist |

### Structure & layout

| Tag | What it produces |
|---|---|
| `{sidetoside}` | Two-column title + description card |
| `{externalsource}` | External link card with title and description |
| `{verticalstepper}` | Vertical numbered step list |
| `{processsnippet}` | Horizontal process cards with arrows |
| `{dividernumber}` | Numbered section dividers |
| `{bluelineseparator}` | Thin horizontal blue rule |
| `{quoteperson}` | Quote block with person photo and citation |

### Text & code

| Tag | What it produces |
|---|---|
| `{textXXL}` | Oversized display text |
| `{formattedbullets}` | Styled numbered list with circles |
| `{codeblock}` | Formatted block of code |
| `{inlinecode}` | Inline code span |

---

## Tags that need extra information

Some snippets need you to supply parameters on the same line as the tag, separated by `|` (pipe character).

**Video**
```
{videoembed}WISTIA_ID_HERE|Title of the video
```

**External source card**
```
{externalsource}Card title|Short description|https://link.com|Link button text
```

**On-page quiz** — put `(correct)` after the right answer
```
{onpagequiz}
Which component stores raw event data?
- Data Pool (correct)
- Data Model
- Studio App
- Extractor
```

---

## Accordion and tabs

For accordions, write the title and content for each item below the tag. Claude will group consecutive items into a single accordion block.

```
{Accordion}
**What is a Data Pool?**
A Data Pool is where raw event data is stored and processed.

{Accordion}
**What is a Data Model?**
A Data Model transforms raw data into a structured view for analysis.
```

For tabs, the first line after the tag becomes the first tab label, and each new bold line starts a new tab:

```
{Tabs}
**Overview**
High-level description of the feature.

**Step-by-step**
Detailed instructions here.

**Example**
A worked example.
```

---

## Tips to make conversion easier

- **One tag per block** — don't stack two tags with no content between them.
- **Tags on their own paragraph** — no text before or after the tag on the same line.
- **Keep tables as tables** — don't use images of tables or fake tables with tabs/spaces.
- **Name your videos** — always include the Wistia ID and a descriptive title in the tag line; it saves a manual lookup later.
- **Mark the correct quiz answer** — add `(correct)` immediately after the answer text; without it Claude will leave a placeholder.
- **Image placeholders are fine** — if a screenshot isn't ready yet, write `[Insert: description of what goes here]` and Claude will create a placeholder in the HTML with a note for the designer.

---

## What happens if you deviate

Claude is tolerant of natural language variations — `{note}`, `{tip}`, `{blue box}` will all map to `{infobox}` and the conversion report will flag it. The closer you stick to the exact tag names above, the fewer flags you'll see. Unrecognised tags never break the conversion — they emit a `<!-- TODO -->` comment in the HTML so nothing is silently lost.
