---
name: "write-alt-text"
description: "Write accurate WCAG 2.2 AA alt text for course images by looking at the image itself and the text around it, deciding decorative vs. informative vs. linked automatically, and asking the designer only about images it is genuinely unsure of. Runs inline from convert-course-to-html, accessibility-check and migrate-rise-export so designers do not need to invoke it; also use it directly when someone asks to 'write alt text', 'describe this image for accessibility', 'is this image decorative', or 'alt text for this screenshot'."
---

# Write Alt Text

Produces alt text that follows `reference/alt-text-guidelines.md` (read it before the first image of a
run — it holds the rules, the role table and the ask/don't-ask table). The designer's effort should be
close to zero: this skill gathers its own context, looks at every image, decides what it can, and asks
one batched question round for the rest.

Mostly this skill is **called by other skills**, with a list of images and the place they live
(script `.md`, generated HTML, or live-page HTML). Standalone, treat whatever the user provides
(image file, URL, pasted HTML, or a screenshot) as the input list.

## Step 1 — Collect each image and its context (no questions)

For every image, gather:

- **Position and neighbours:** the heading, plus the one or two paragraphs before and after it, from the
  script or HTML you already have.
- **Caption**, if any (`<figcaption>`, snippet caption, or the line under a script placeholder).
- **Link status:** is the `<img>` wrapped in `<a href>` or `<button>`? Note the destination.
- **Script hints:** a placeholder tag such as `[Image placeholder - desc | purpose: decorative]`
  or `purpose: link:<dest>`. Follow it.
- **Existing alt**, if any (Rise exports and live courses often have some; keep it if it already meets
  the guidelines, fix it if not).

## Step 2 — Look at the image

Open the image with the Read tool so you actually see it:

| Image source | How to get it |
|---|---|
| Local file (`04_Assets/`, Drive download, Rise `assets/`) | Read it directly |
| On the Celonis CDN (live course, extracted HTML) | `curl -L "<url>" -o <temp folder>/<file>`, then Read it. If the download fails, continue with context only and mark the image **low-confidence** |
| Placeholder, no file yet | Context only (the script description); mark **provisional** |

Note: image type (screenshot, diagram, chart, photo, icon, banner), all visible text (labels, menu
items, numbers), the key UI elements or relationships, and whether the image is *about* its text.
Compare with the neighbouring text: what does the image say that the text does not?

Known limits — flag instead of guessing: animated GIFs (you only see one frame), very small or
dense screenshot text you cannot read confidently, charts with many data points (use the long-description
path, never invent numbers).

## Step 3 — Decide

Apply the "automatic decisions" table in the guidelines. In short:

- Linked image, destination known: alt = destination.
- Informative and not covered by nearby text: alt of two sentences at most, no "image of".
- Decorative, or fully covered by the adjacent text or caption: `alt=""`.
- Too dense for two sentences: one-sentence alt ending "Detailed description below the image." plus an
  `{Accordion}` titled `Description of the image: [title]` with a description of at most 20 lines, marked as a
  draft for review.

Anything that hits an "ask" trigger (link destination unknown, ambiguous role, partial overlap,
unreadable image, GIF, provisional alt) gets your best-guess alt and goes on the **uncertain list**.
Do not stop to ask yet.

## Step 4 — One batched question round

If the uncertain list is non-empty, ask with `AskUserQuestion` (up to 4 questions per call; send further
calls for more). Never one image at a time across the run, and never for images you decided confidently.

Each question must let the owner recognise the image without code identifiers: say where it is (page,
heading, what comes right before/after) and what it shows, quote your proposed alt text, and offer
options such as:

- "Use proposed alt text"
- "Make decorative (empty alt)"
- "It's a link to … / needs long description" (the user can type the destination or details via Other)

Apply the answers. If the owner wanted more detail than two sentences, use the long-description path.
Never add a question just to confirm something you were already confident about.

## Step 5 — Write results and the log

- Return the final `alt` for each image to the calling skill (or apply it when running standalone and the
  owner asked for edits). Remove any `<!-- ALT CHECK -->` markers once resolved.
- Create or update `alt-text-log.md` in the course's `03_HTML/` folder (standalone with no course folder:
  next to the input), one row per image:

  | Page | Image (position / what it shows) | Alt text | Decision |
  |---|---|---|---|

  `Decision` is one of: informative, linked, decorative, covered by text, long description. Keep empty alts
  in the table (Localization needs to know they are deliberate).
- Close with one short message: how many images were handled automatically vs. asked about, where the log
  is, and one reminder that the wording is theirs to review and edit before publishing. Thank them.

## Rules for yourself

- Never propose alt text that starts with "image of", "graphic of" or "screenshot of".
- Never exceed two sentences in the `alt` attribute.
- Never invent content that is not visible in the image or stated in the page.
- Do not change anything except the alt attribute (and the accordion, if the long-description path is
  chosen). Page wording and layout are out of scope.
- Plain language when talking to the owner; do not mention this preference.
