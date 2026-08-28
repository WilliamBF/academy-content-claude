# -*- coding: utf-8 -*-
"""
ti_extract_parse.py - Parse a TI course extract JSON into .md files.

Output structure: one .md file per lesson (topics as ## sections within).
  <output_dir>/<course-slug>/
    _index.md                          <- table of contents
    <section-slug>/<lesson-slug>.md    <- one file per lesson

Usage:
    python ti_extract_parse.py <raw_json_path> <output_dir>

<raw_json_path>  JSON produced by ti_extract_run.py (or legacy MCP format)
<output_dir>     Root folder; a subfolder named after the course slug is created inside
"""

import json
import re
import sys
from pathlib import Path


# -- slugify -------------------------------------------------------------------

def slugify(text, seen=None):
    text = text or "untitled"
    s = re.sub(r"[^\w\s-]", "", text.lower())
    s = re.sub(r"[\s_]+", "-", s).strip("-")[:60]
    if seen is not None:
        base = s
        n = 2
        while s in seen:
            s = f"{base}-{n}"
            n += 1
        seen.add(s)
    return s


# -- HTML -> Markdown ----------------------------------------------------------

def html_to_md(h):
    if not h:
        return ""
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"</(p|div|li|tr)>", "\n", h, flags=re.I)
    h = re.sub(r"<(p|div)[^>]*>", "\n", h, flags=re.I)
    for n in range(6, 0, -1):
        h = re.sub(
            rf"<h{n}[^>]*>(.*?)</h{n}>",
            lambda m, n=n: "\n" + "#" * n + " " + m.group(1) + "\n",
            h, flags=re.I | re.S,
        )
    h = re.sub(r"<[ou]l[^>]*>", "\n", h, flags=re.I)
    h = re.sub(r"</[ou]l>", "\n", h, flags=re.I)
    h = re.sub(
        r"<li[^>]*>(.*?)</li>",
        lambda m: "- " + m.group(1).strip() + "\n",
        h, flags=re.I | re.S,
    )
    h = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", h, flags=re.I | re.S)
    h = re.sub(r"<b[^>]*>(.*?)</b>",           r"**\1**", h, flags=re.I | re.S)
    h = re.sub(r"<em[^>]*>(.*?)</em>",         r"*\1*",   h, flags=re.I | re.S)
    h = re.sub(r"<i[^>]*>(.*?)</i>",           r"*\1*",   h, flags=re.I | re.S)
    h = re.sub(r"<code[^>]*>(.*?)</code>",     r"`\1`",   h, flags=re.I | re.S)
    h = re.sub(
        r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        r"[\2](\1)", h, flags=re.I | re.S,
    )
    h = re.sub(r"<table[^>]*>", "\n", h, flags=re.I)
    h = re.sub(r"</table>", "\n", h, flags=re.I)
    h = re.sub(r"<tr[^>]*>", "", h, flags=re.I)
    h = re.sub(r"</tr>", "\n", h, flags=re.I)
    h = re.sub(
        r"<t[dh][^>]*>(.*?)</t[dh]>",
        lambda m: "| " + m.group(1).strip() + " ",
        h, flags=re.I | re.S,
    )
    h = re.sub(r"<[^>]+>", "", h)
    for old, new in [
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&nbsp;", " "),
        ("&#39;", "'"), ("&quot;", '"'), ("“", '"'), ("”", '"'),
        ("‘", "'"), ("’", "'"), ("–", "-"), ("—", "--"),
    ]:
        h = h.replace(old, new)
    h = re.sub(r"\n{3,}", "\n\n", h)
    return h.strip()


# -- helpers -------------------------------------------------------------------

def _meta_line(t):
    """Return a one-line italicised metadata string for contentDescription/Estimate/Time."""
    parts = []
    if t.get("contentDescription"):
        parts.append(t["contentDescription"])
    if t.get("contentEstimate"):
        parts.append(f"Estimate: {t['contentEstimate']}")
    if t.get("contentTime"):
        parts.append(f"Time: {t['contentTime']}")
    return "*" + "  |  ".join(parts) + "*" if parts else ""


def _pre_post(t):
    """Return (pre_md, post_md) for preTextBlock / postTextBlock."""
    return (
        html_to_md(t["preTextBlock"]) if t.get("preTextBlock") else "",
        html_to_md(t["postTextBlock"]) if t.get("postTextBlock") else "",
    )


# -- topic content dispatch -----------------------------------------------------

# Only types with zero extractable text remain here.
SKIPPED_TYPES = {
    "QuizPage", "SurveyPage", "WorkbookPage",
    "ScormPage", "MeetingPage", "TallyPage", "GeneralPage",
}


def topic_content(t):
    tn = t.get("__typename", "UnknownPage")

    if tn in SKIPPED_TYPES:
        return f"*[{tn}]*"

    # ------------------------------------------------------------------ text/body pages

    if tn == "TextPage":
        parts = [html_to_md(t.get("body", ""))]
        m = _meta_line(t)
        if m:
            parts.append(m)
        return "\n\n".join(p for p in parts if p)

    if tn == "NotebookPage":
        parts = [html_to_md(t.get("body", ""))]
        m = _meta_line(t)
        if m:
            parts.append(m)
        return "\n\n".join(p for p in parts if p)

    if tn == "ArticlePage":
        parts = []
        for f in ("body", "contentDescription"):
            if t.get(f):
                parts.append(html_to_md(t[f]))
        m = _meta_line(t)
        if m:
            parts.append(m)
        return "\n\n".join(p for p in parts if p)

    # ------------------------------------------------------------------ media pages

    if tn == "VideoPage":
        parts = []
        for f in ("preTextBlock", "body"):
            if t.get(f):
                parts.append(html_to_md(t[f]))
        parts.append(f"*[Video -- ID: {t.get('id', 'unknown')}]*")
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(parts)

    if tn == "AudioPage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        if t.get("caption"):
            parts.append(html_to_md(t["caption"]))
        parts.append("*[Audio resource -- not extractable as text]*")
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(parts)

    if tn == "PDFViewerPage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        parts.append("*[PDF viewer -- content not extractable as text]*")
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(parts)

    if tn == "HtmlEmbedPage":
        scripts = t.get("scripts", "")
        if scripts:
            return html_to_md(scripts)
        return "*[HTML embed -- no extractable text]*"

    # ------------------------------------------------------------------ interactive/structured pages

    if tn == "HighlightZonePage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        for z in t.get("highlightZones", []):
            title = z.get("title", "")
            caption = html_to_md(z.get("caption", ""))
            alt = z.get("altText", "")
            zone_parts = []
            if title:
                zone_parts.append(f"### {title}")
            if caption:
                zone_parts.append(caption)
            if alt:
                zone_parts.append(f"*Alt: {alt}*")
            if zone_parts:
                parts.append("\n".join(zone_parts))
        if t.get("altText"):
            parts.append(f"*Image alt: {t['altText']}*")
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn == "ListRollPage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        if t.get("description"):
            parts.append(html_to_md(t["description"]))
        for el in t.get("expandableLists", []):
            items = "\n".join(
                f"- **{i.get('title', '')}** -- {html_to_md(i.get('description', ''))}"
                + (f" *Alt: {i['altText']}*" if i.get("altText") else "")
                for i in el.get("expandableListItems", [])
            )
            parts.append(f"### {el.get('title', '')}\n{items}")
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn == "FlipCardPage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        for c in t.get("flipCards", []):
            title = c.get("title", "")
            front = html_to_md(c.get("frontText", ""))
            back = html_to_md(c.get("description", ""))
            alt = c.get("altText", "")
            card_lines = []
            if title:
                card_lines.append(f"### {title}")
            if front:
                card_lines.append(f"**Front:** {front}")
            if back:
                card_lines.append(f"**Back:** {back}")
            if alt:
                card_lines.append(f"*Alt: {alt}*")
            if card_lines:
                parts.append("\n".join(card_lines))
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn in ("PresentationPage", "SlideshowPage"):
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        for i, s in enumerate(t.get("slides", []), 1):
            title = s.get("title", "")
            caption = html_to_md(s.get("caption", ""))
            alt = s.get("altText", "")
            slide_lines = [f"### Slide {i}" + (f": {title}" if title else "")]
            if caption:
                slide_lines.append(caption)
            if alt:
                slide_lines.append(f"*Alt: {alt}*")
            parts.append("\n".join(slide_lines))
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn == "InteractivePage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        tags = [tag for tag in t.get("tags", []) if tag.get("caption")]
        if tags:
            parts.append(
                "**Hotspots:**\n" + "\n".join(
                    f"- {html_to_md(tag['caption'])}" for tag in tags
                )
            )
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn == "AssignmentPage":
        parts = []
        for f in ("preTextBlock", "description"):
            if t.get(f):
                parts.append(html_to_md(t[f]))
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn == "MatchPairPage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        pairs = t.get("matchPairs", [])
        if pairs:
            lines = []
            for pair in pairs:
                clue = pair.get("clue", "")
                caption = html_to_md(pair.get("caption", ""))
                label = pair.get("label", "")
                entry = f"- **{clue}** -> {caption}"
                if label:
                    entry += f" *(label: {label})*"
                lines.append(entry)
            parts.append("**Match pairs:**\n" + "\n".join(lines))
        if t.get("postTextBlock"):
            parts.append(html_to_md(t["postTextBlock"]))
        return "\n\n".join(p for p in parts if p)

    if tn == "RecipePage":
        parts = []
        if t.get("preTextBlock"):
            parts.append(html_to_md(t["preTextBlock"]))
        if t.get("description"):
            parts.append(html_to_md(t["description"]))
        meta_items = []
        if t.get("time"):
            meta_items.append(f"Time: {t['time']}")
        if t.get("yield"):
            meta_items.append(f"Yield: {t['yield']}")
        if meta_items:
            parts.append("*" + "  |  ".join(meta_items) + "*")
        if t.get("pairing"):
            parts.append(html_to_md(t["pairing"]))
        for ig in t.get("ingredientGroups", []):
            label = ig.get("label", "Ingredients")
            items = "\n".join(
                f"- {i.get('value', '')}" for i in ig.get("ingredients", [])
            )
            parts.append(f"**{label}**\n{items}")
        for idx, step in enumerate(t.get("steps", []), 1):
            body = html_to_md(step.get("body", ""))
            if body:
                parts.append(f"**Step {idx}:** {body}")
        return "\n\n".join(p for p in parts if p)

    if tn == "TestPage":
        parts = []
        for label, field in [
            ("Start", "startMessage"),
            ("Pass", "passMessage"),
            ("Fail", "failMessage"),
        ]:
            if t.get(field):
                parts.append(f"**{label}:** {html_to_md(t[field])}")
        return "\n\n".join(parts) if parts else "*[Test page -- no messages found]*"

    # ------------------------------------------------------------------ generic fallback

    parts = []
    for field in ("preTextBlock", "body", "description", "scripts"):
        if t.get(field):
            parts.append(html_to_md(t[field]))
    if t.get("postTextBlock"):
        parts.append(html_to_md(t["postTextBlock"]))
    if parts:
        return "\n\n".join(parts)
    return f"*[{tn} -- no extractable text found]*"


# -- main -----------------------------------------------------------------------

def _write_learning_path(lp: dict, out_base_root: Path):
    """Write a learning path _index.md listing milestones and courses."""
    name = lp.get("name") or lp.get("title") or "learning-path"
    slug = slugify(name)
    out_base = out_base_root / slug
    out_base.mkdir(parents=True, exist_ok=True)

    lines = [f"# {name} (Learning Path)", ""]
    if lp.get("shortDescription"):
        lines += [lp["shortDescription"], ""]
    lines += [f"**ID:** `{lp['id']}`", "", "---", ""]

    milestones = lp.get("milestones", [])
    for idx, ms in enumerate(milestones, 1):
        lines.append(f"## Milestone {idx}: {ms.get('name', '(untitled)')}")
        lines.append("")
        courses = ms.get("courses", [])
        if courses:
            lines.append("| Title | Course ID |")
            lines.append("|---|---|")
            for c in courses:
                title = c.get("title", "(untitled)")
                cid = c.get("id", "")
                desc = c.get("description", "")
                lines.append(f"| {title} | `{cid}` |")
                if desc:
                    lines.append(f"| *{desc[:120]}* | |")
        lines.append("")

    lines.append(
        "> To extract the full content of any course listed above, run:\n"
        "> `/extract-TI-course` with the Course ID shown in the table."
    )

    n_courses = sum(len(m.get("courses", [])) for m in milestones)
    out_path = out_base / "_index.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Learning path: {name}")
    print(f"Milestones: {len(milestones)}  |  Courses: {n_courses}")
    print(f"Output: {out_path}")


def main():
    if len(sys.argv) != 3:
        print("Usage: python ti_extract_parse.py <raw_json_path> <output_dir>")
        sys.exit(1)

    raw_path = Path(sys.argv[1])
    out_base_root = Path(sys.argv[2])

    with open(raw_path, encoding="utf-8") as f:
        outer = json.load(f)

    # Unwrap MCP tool-result envelope if present
    if isinstance(outer, list) and outer and "text" in outer[0]:
        data = json.loads(outer[0]["text"])
    else:
        data = outer

    # Detect learning path vs course envelope
    lp = data.get("data", {}).get("LearningPath")
    if lp:
        _write_learning_path(lp, out_base_root)
        return

    cg = data["data"]["CourseGroupBySlug"]
    course_title = cg["title"]
    course_slug = slugify(course_title)
    course = cg["courses"][0]
    sections = course["sections"]

    out_base = out_base_root / course_slug
    out_base.mkdir(parents=True, exist_ok=True)

    # Build index and write one file per lesson
    index_lines = [f"# {course_title}\n"]
    lessons_written = 0
    topics_total = 0
    type_counts = {}
    skipped = 0

    for sec in sections:
        sec_slug = slugify(sec["title"])
        sec_dir = out_base / sec_slug
        sec_dir.mkdir(parents=True, exist_ok=True)

        index_lines.append(f"\n## {sec['title']}\n")

        for les in sec["lessons"]:
            les_slug = slugify(les["title"])
            les_path = sec_dir / f"{les_slug}.md"

            index_lines.append(f"- [{les['title']}]({sec_slug}/{les_slug}.md)")

            # Build lesson file: frontmatter + H1 + one ## per topic
            lines = [
                "---",
                f"course: {course_title}",
                f"section: {sec['title']}",
                f"lesson: {les['title']}",
                "---",
                "",
                f"# {les['title']}",
                "",
            ]

            for t in les["topics"]:
                tn = t.get("__typename", "UnknownPage")
                type_counts[tn] = type_counts.get(tn, 0) + 1
                topics_total += 1

                content = topic_content(t)
                if tn in SKIPPED_TYPES:
                    skipped += 1

                lines.append(f"## {t.get('title', '(untitled)')}")
                lines.append(f"<!-- type: {tn}  id: {t.get('id', '')} -->")
                lines.append("")
                if content:
                    lines.append(content)
                    lines.append("")

            les_path.write_text("\n".join(lines), encoding="utf-8")
            lessons_written += 1

    (out_base / "_index.md").write_text("\n".join(index_lines), encoding="utf-8")

    text_rich = {k: v for k, v in type_counts.items() if k not in SKIPPED_TYPES}
    print(f"Course: {course_title}")
    print(
        f"Sections: {len(sections)}  |  "
        f"Lessons: {lessons_written}  |  "
        f"Topics: {topics_total}"
    )
    print("Text-rich types: " + ", ".join(f"{k} {v}" for k, v in sorted(text_rich.items())))
    print(f"Skipped (no text): {skipped}")
    print(f"Output: {out_base}")


if __name__ == "__main__":
    main()
