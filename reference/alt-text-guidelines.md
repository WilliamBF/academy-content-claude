# Alt text guidelines (WCAG 2.2 AA)

Single source of truth for how Celonis Academy images get their alt text. `write-alt-text`,
`convert-course-to-html`, `accessibility-check` and `write-course-script` all point here — change the
rule here, not in those files.

Alt text is the textual substitute for an image. Screen readers read it instead of the image, it
shows when an image fails to load, and search engines use it. Screen readers already announce
"graphic" before reading it, so the alt text only has to carry the **content and function** of the image.

---

## 1. Decide the image's role first

| Role | What it is | Alt text |
|---|---|---|
| **Decorative** | Layout or mood only, no information a learner needs, not a link. Test: *if the image were deleted, would important content be lost?* If no, it is decorative. | `alt=""` (empty, never filler text) |
| **Covered by adjacent text** | The surrounding text or caption already presents the full content of the image | `alt=""` |
| **Informative** | Screenshot, diagram, chart or photo that carries content the learner needs | Describe the content (section 2) |
| **Linked** | Image sits inside an `<a>` or a `<button>` | Describe where the link goes (section 3) |

An image only has a *function* if it is linked or inside a button.

## 2. Writing the alt text

1. Content and function first: what does the learner need from this image, in this place on the page?
2. Never start with "image of", "graphic of", "screenshot of" or similar. Mention the format only when it
   is itself the point (for example, a photograph vs. an illustration).
3. Only include what is in the image. Do not add background, interpretation, or text that is not shown.
4. Be accurate and equivalent: someone who cannot see the image should be able to follow the lesson.
5. Be succinct. Usually a few words; **never more than two sentences**.
6. Do not repeat the caption or the paragraph next to it. Add only what they do not already say.
7. Use inclusive language, consistent with `reference/celonis_content_style_guide.md`.
8. Use `&rarr;` / `&larr;` for arrows, never literal arrow characters.

## 3. Linked images

Alt text describes the **destination**, not the picture. Example: a wolf photo linking to Wikipedia gets
`alt="Wikipedia entry for Wolf"`. If the text right next to the image already says where the link goes,
describe only what the image adds (or leave it empty if it adds nothing).

## 4. When two sentences are not enough

Complex diagrams, dense screenshots, charts with many data points. Do **not** write a long alt text.
Instead:

- Put the description in the page text where it fits naturally, **or**
- Add an `{Accordion}` directly below the image, titled `Description of the image: [image title]`,
  containing the detailed description (at most 20 lines), **and**
- Shorten the alt text to one sentence ending in "Detailed description below the image."

A description Claude drafts for the accordion is always a **draft for the owner to review and edit**.

Images of text: avoid using an image as a stand-in for real text (it cannot be localized or read). This
does not apply to screenshots, graphs and diagrams that combine text with other meaningful content.

## 5. Where alt text lives

- In HTML: the `alt` attribute on `<img>`.
- In the Thought Industries editor: click the image, **Edit**, and fill in the **Title** field. That field
  is the alt text.
- Remove inline `style`, `width` and `height` from `<img>`, `<figure>` and their wrapping `<p>`.

## 6. Automatic decisions vs. questions (used by `write-alt-text`)

The designer should not have to answer questions Claude can work out. Context comes from the script,
the HTML around the image, the caption, any `<a>` wrapper and the image itself.

| Situation | Decision |
|---|---|
| Image inside `<a>` with a known `href` | Linked: alt = destination |
| Screenshot/diagram whose content is not stated in nearby text | Informative: write alt (two sentences max) |
| Adjacent text or caption fully states the image content | `alt=""` |
| Pure banner, divider, background, stock photo with no teaching content | `alt=""` |
| Content too dense for two sentences | Short alt + drafted accordion description |
| Script placeholder carries `purpose:` tag | Follow the tag |

**Ask (batched, one round per page or per run) only when:**

- the image is clearly a link but the destination cannot be determined,
- decorative vs. informative is genuinely ambiguous,
- nearby text overlaps the image content only partly,
- the image could not be read (download failed, too small, unreadable text) and the alt is a guess,
- the image is an animated GIF (only the first frame can be seen).

Always remind the owner, once at the end, to review the wording themselves.

## 7. Localization hand-off

Every alt text, including deliberate empty ones, is recorded in `alt-text-log.md` (page, image, alt text,
decision) so the Localization team can translate it. `write-alt-text` creates and updates this file; the
owner does not have to compile it.
