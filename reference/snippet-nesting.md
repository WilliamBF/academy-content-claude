# Snippet Nesting

Single source of truth for putting one snippet inside another. Read by `write-course-script` (what to tag), `convert-course-to-html` (how to render it) and `upload-course-to-TI` (what to warn about).

Results below come from two push-and-review rounds on a test course (27 two-level combinations, reviewed in the LMS by the course owner). Re-test and update the matrix when the LMS CSS changes.

---

## Syntax

Flat tags are unchanged: `{tag}` applies until the next heading or tag. A snippet that **contains** other snippets uses an explicit close tag, `{/tag}`, on its own line.

```
{different-color}
Intro sentence inside the blue background.
{codeblock}
SELECT * FROM table;
{/codeblock}
{externalsource}Guide title|Short description|https://link.com|Open guide
{/different-color}
```

Rules:

1. **Close the parent.** Every container with children needs `{/parent}`. Without it the converter treats the tags as flat siblings.
2. **Close a child when more content follows it in the same slot.** The last child before `{/parent}` may omit its own close tag.
3. **Two levels only** (parent > child). A third level is flagged and rendered as a flat sibling instead.
4. **Tabs:** a bold line starts each tab; children go under it; `{/Tabs}` ends the group.
5. **Accordion:** each `{Accordion}` item holds its own children; `{/Accordion}` ends the group. Consecutive flat `{Accordion}` items still merge as before.
6. **Plain text** inside a container is a normal paragraph in that slot.
7. **Legacy bracket markers** (`[Blue box start]`, `[Tabs start]`, ...) keep working but do not support children.

---

## Where children go (content slots)

| Parent | Slot (child markup is placed here, with no extra wrapper) |
|---|---|
| `{Tabs}` | inside the tab's `div.snippet--tabs-content` |
| `{Accordion}` | inside the item's `div.accordion-content` |
| `{different-color}` | inside `div.different-color`, after the optional bold title line |
| `{infobox}` / `{infobox with title}` | inside `div.infobox-text` |
| `{internalcontent}` | inside `div.snippet--internal-content`, after the disclaimer |

Every other snippet is a **leaf**: it cannot contain other snippets.

---

## Support matrix

Verified = rendered and behaved correctly in the LMS. Avoid = tested and broken or ugly. Untested = not tried; do not use without a test.

### Tabs (panel) and Accordion (item)

| Child | Tabs | Accordion |
|---|---|---|
| infobox | Verified | Verified |
| imagetextleft | Verified | Verified |
| imagetextright / center | Untested | Untested |
| formattedbullets | Verified | Verified |
| codeblock | Verified | Untested |
| externalsource | Untested | Verified |
| onpagequiz | Untested | Verified |
| Accordion | Verified | n/a (no accordion in accordion) |
| Tabs | n/a (no tabs in tabs) | Verified |
| carousel, videoembed, checkbox lists | Untested | Untested |

### different-color (preferred blue-background container)

Full page width. Holds **any number of stacked children** (tested up to 5 in a row).

| Child | Status |
|---|---|
| externalsource | Verified |
| imagetextleft / imagetextright | Verified |
| codeblock | Verified |
| formattedbullets, plain bullet or numbered list | Verified |
| Accordion | Verified |
| Tabs | Verified |
| onpagequiz | Verified |
| carousel, videoembed, checkbox lists | Untested |

### infobox / infobox with title (reduced width, short callouts only)

| Child | Status |
|---|---|
| imagetextleft / imagetextright | Verified |
| codeblock, inlinecode | Verified |
| **formattedbullets** | **Avoid** (renders badly in the narrow box; use `{different-color}`) |
| Accordion, Tabs, onpagequiz, externalsource, plain lists | Untested; prefer `{different-color}` |

### internalcontent

| Child | Status |
|---|---|
| infobox | Verified |
| Everything else | Untested |

### Leaves that must not contain snippets

| Parent | Status |
|---|---|
| **onpagequiz > Accordion** (inside the quiz shell) | **Avoid for now.** The accordion labels turn white after a click because the quiz styling reaches every button inside it. A CSS fix is planned; place the accordion **after** the quiz instead (verified). Update this row when the fix ships. |
| onpagequiz > anything else | Untested; treat as a leaf |

---

## Choosing the container

- Blue background around mixed content, lists, quizzes, accordions or tabs: **`{different-color}`**.
- One short key point or warning: `{infobox}`. Keep it to text, an image or code.
- Content hidden until clicked: `{Accordion}`. Parallel options: `{Tabs}`.
- Need an accordion below a quiz: put `{Accordion}` after `{/onpagequiz}`, not inside it.

## Callout limit

`{different-color}` used as a container is **not** counted as a callout. `{infobox}` always is: at most one per page, and an infobox nested inside Tabs, an Accordion or internalcontent counts toward that limit.

## Page hygiene when nesting

- **Unique ids per page.** `onpagequiz` (`#result`), `checkboxrounded` / `checkboxsquare` (`r1..r8`, `c1..c8`) and `carousel` (`id` + `aria-controls`) use ids. Do not repeat the same snippet with the same ids on one page.
- **No headings inside a slot.** Use a bold line; headings stay at page level (one `<h1>`, max `<h3>`).
- **No nested interactive of the same kind** (Accordion in Accordion, Tabs in Tabs).
- Nesting does not change the Wistia, image-upload or alt-text steps; children follow their normal rules.
