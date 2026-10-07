#!/usr/bin/env python3
"""
rise_extractor.py
Articulate Rise 360 zip export -> Thought Industries payload (HTML preview + JSON)
or a reviewable Word (.docx) document, with assets extracted alongside.

Part of the `migrate-rise-export` skill. This script only does extraction — it
never talks to the TI API and never uploads images anywhere. Hand its output to
the plugin's existing `convert-course-to-html` (image_uploader.py / patch_cdn_urls.py)
and `upload-course-to-TI` (ti_uploader.py) skills for the CDN-upload and push steps;
see SKILL.md in this folder for the full chain.

Usage:
  python rise_extractor.py <rise-export.zip> --output <dir> [--format html|docx]

Output (written into <dir>):
  html format: assets/, <Course_Title>.html, <Course_Title>_payload.json
  docx format: assets/, <Course_Title>.docx   (no payload JSON — review-only)

The HTML/JSON output embeds images as:
  <img src="PENDING_CDN_UPLOAD" data-local="assets/<filename>" alt="..." />
This placeholder is resolved by `convert-course-to-html/image_uploader.py` +
`patch_cdn_urls.py` in the next step of the chain — do not push a payload to TI
while PENDING_CDN_UPLOAD markers remain (ti_uploader.py --check-pending enforces this).
"""

import argparse
import os
import base64
import json
import re
import sys
import zipfile
import urllib.parse

# Force UTF-8 stdout/stderr so the box-drawing/arrow characters used in this
# script's print statements don't crash under a Windows console's legacy
# cp1252 default encoding (reconfigure() is Python 3.7+; harmless no-op elsewhere).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, ValueError):
        pass

try:
    from bs4 import BeautifulSoup, NavigableString
except ImportError:
    print("The 'beautifulsoup4' library is not installed. Please run: pip install beautifulsoup4")
    sys.exit(1)

try:
    import docx
    from docx.shared import Inches, Pt, RGBColor
    _DOCX_AVAILABLE = True
except ImportError:
    _DOCX_AVAILABLE = False

try:
    from PIL import Image as _PILImage
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
# HTML / Payload Helpers
# ─────────────────────────────────────────────────────────────────────────────

def promote_table_headers(html_text):
    """Convert a bolded first <tr> of plain <td> cells into a real <thead><th scope="col">
    row so TI's table styling applies. Tables that already have a <thead> are left alone
    (only backfilling a missing scope="col"). Tables whose first row isn't unambiguously
    a bold-only header row are left untouched rather than guessed at."""
    if '<table' not in html_text:
        return html_text
    soup = BeautifulSoup(html_text, 'html.parser')
    tables = soup.find_all('table')
    if not tables:
        return html_text

    changed = False
    for table in tables:
        thead = table.find('thead', recursive=False)
        if thead:
            for th in thead.find_all('th'):
                if not th.has_attr('scope'):
                    th['scope'] = 'col'
                    changed = True
            continue

        tbody = table.find('tbody', recursive=False)
        row_container = tbody if tbody else table
        rows = row_container.find_all('tr', recursive=False)
        if not rows:
            continue
        first_tr = rows[0]
        cells = first_tr.find_all(['td', 'th'], recursive=False)
        if not cells:
            continue

        def _is_pure_strong(cell):
            kids = [c for c in cell.contents if not (isinstance(c, str) and not c.strip())]
            return len(kids) == 1 and getattr(kids[0], 'name', None) == 'strong'

        if not all(_is_pure_strong(c) for c in cells):
            continue

        new_thead = soup.new_tag('thead')
        new_tr = soup.new_tag('tr')
        for cell in cells:
            strong = cell.find('strong')
            th = soup.new_tag('th')
            th['scope'] = 'col'
            strong.extract()
            th.append(strong)
            strong.unwrap()
            new_tr.append(th)
        new_thead.append(new_tr)

        first_tr.extract()
        if tbody:
            tbody.insert_before(new_thead)
        else:
            new_tbody = soup.new_tag('tbody')
            for tr in list(table.find_all('tr', recursive=False)):
                tr.extract()
                new_tbody.append(tr)
            table.append(new_tbody)
            table.insert(0, new_thead)
        changed = True

    return str(soup) if changed else html_text

def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'\sstyle="[^"]*"', '', text)
    text = re.sub(r'\sdata-editor-id="[^"]*"', '', text)
    text = re.sub(r'\sclass="[^"]*"', '', text)
    text = re.sub(r'\sdir="[^"]*"', '', text)
    text = re.sub(r'<\/?span[^>]*>', '', text)
    text = re.sub(r'<\/?div[^>]*>', '', text)
    text = text.replace('<strong>Heading</strong>', '')
    text = re.sub(r'<p>\s*(?:<br\s*/?>)?\s*</p>', '', text)
    if '<table' in text:
        text = promote_table_headers(text)
    return text.strip()

# ─────────────────────────────────────────────────────────────────────────────
# Title casing (for Rise lesson/topic titles, which are inconsistently cased)
# ─────────────────────────────────────────────────────────────────────────────

_TITLE_MINOR_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "in", "nor", "of",
    "on", "or", "per", "the", "to", "v", "via", "vs", "with",
}

_TITLE_ACRONYMS = {
    "kpi": "KPI", "kpis": "KPIs", "olap": "OLAP", "sql": "SQL", "ai": "AI",
    "api": "API", "id": "ID", "url": "URL", "pdf": "PDF", "ui": "UI",
    "ux": "UX", "faq": "FAQ", "po": "PO", "tt": "TT",
}

def _title_case_word(word, is_edge):
    m = re.match(r'^(\W*)([A-Za-z]+)(\W*)$', word)
    if not m:
        return word
    lead, core, trail = m.groups()
    lower = core.lower()
    if lower in _TITLE_ACRONYMS:
        cased = _TITLE_ACRONYMS[lower]
    elif not is_edge and lower in _TITLE_MINOR_WORDS:
        cased = lower
    else:
        cased = core[:1].upper() + core[1:].lower()
    return lead + cased + trail

def to_title_case(title):
    """Standard title case with acronym preservation. Fixes Rise's inconsistent
    auto-capitalization (e.g. 'cONFIGURE CUSTOM KPIS [30 min]' -> 'Configure Custom
    KPIs [30 min]') without touching genuine source typos."""
    if not title:
        return title
    m = re.match(r'^(.*\S)(\s*\[[^\]]*\])\s*$', title)
    if m:
        body, tag = m.group(1), m.group(2)
    else:
        body, tag = title, ''
    words = body.split(' ')
    out_words = []
    for i, word in enumerate(words):
        is_edge = (i == 0 or i == len(words) - 1)
        segments = word.split('-')
        cased_segments = [_title_case_word(seg, is_edge) for seg in segments]
        out_words.append('-'.join(cased_segments))
    return ' '.join(out_words) + tag

def get_image_html(node, assets_prefix="assets"):
    """Return <img> HTML pointing to an extracted Rise asset.
    Uses PENDING_CDN_UPLOAD with data-local for the image_uploader.py workflow."""
    if not isinstance(node, dict):
        return ""
    img_data = node.get('media', {}).get('image', {})
    if not img_data:
        return ""
    filename = urllib.parse.unquote(img_data.get('crushedKey', '')) or img_data.get('originalUrl') or "unknown_image"
    basename = os.path.basename(filename)

    # Prefer contextual Rise fields; fall back to cleaned filename
    raw_alt = (node.get('caption') or node.get('heading') or
               node.get('title') or node.get('paragraph') or "")
    if raw_alt:
        alt = re.sub(r'<[^>]+>', '', raw_alt)          # strip HTML tags
        alt = re.sub(r'&nbsp;', ' ', alt)               # non-breaking spaces
        import html as _html; alt = _html.unescape(alt) # decode &amp; &#39; etc.
        alt = re.sub(r'\s+', ' ', alt).strip()
        if len(alt) > 125:
            alt = alt[:122].rsplit(' ', 1)[0] + '...'
    else:
        alt = re.sub(r'\.[^.]+$', '', basename).replace('-', ' ').replace('_', ' ')

    return f'<img src="PENDING_CDN_UPLOAD" data-local="{assets_prefix}/{basename}" alt="{alt}" />'

def clean_body_content(body):
    if not body:
        return body
    return re.sub(r'\s*\[\d{1,2}(?:[:.]\d{2})?\s*(?:min|mins|m)?\]', '', body)

# ─────────────────────────────────────────────────────────────────────────────
# Asset / zip helpers
# ─────────────────────────────────────────────────────────────────────────────

def extract_assets_from_zip(zip_path, output_dir):
    """Copy content/assets/* from the Rise zip into output_dir/assets/."""
    assets_dir = os.path.join(output_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            if name.startswith("content/assets/") and not name.endswith("/"):
                basename = os.path.basename(name)
                if basename:
                    target = os.path.join(assets_dir, basename)
                    with zf.open(name) as src, open(target, 'wb') as dst:
                        dst.write(src.read())
    count = len(os.listdir(assets_dir))
    print(f"  Extracted {count} asset file(s) to {assets_dir}")
    return assets_dir

def load_runtime_data(source):
    """Decode runtime-data.js from a zip path or a direct .js file path."""
    if source.lower().endswith(".zip"):
        with zipfile.ZipFile(source) as zf:
            with zf.open("content/runtime-data.js") as f:
                s = f.read().decode("utf-8")
    else:
        with open(source, 'r', encoding='utf-8') as f:
            s = f.read()
    b64 = s[s.find(',') + 1:]
    b64 = b64[b64.find('"') + 1:b64.rfind('"')]
    return json.loads(base64.b64decode(b64))

# ─────────────────────────────────────────────────────────────────────────────
# Storyline helpers
# ─────────────────────────────────────────────────────────────────────────────

_STORYLINE_NOISE = re.compile(
    r'play and pause|Rectangular Hotspot|Table with \d|^Operational App|'
    r'^Accounts (Payable|Receivable)$|^Order Management$|^Procurement$',
    re.IGNORECASE
)

def _extract_storyline_slides(zip_path, content_prefix, slides):
    """
    For each slide in `slides`, extract title, description, and the filename of its
    largest mobile screenshot image.  Returns a list of dicts; skips slides that
    reference more than 2 images (navigation/overview slides).
    """
    sl_prefix = f"content/assets/{content_prefix}/"
    result = []

    with zipfile.ZipFile(zip_path) as zf:
        entries = set(zf.namelist())

        # Map image-ID prefix → filename for all mobile PNGs in this Storyline
        mobile_id_map = {}
        for e in entries:
            if e.startswith(f"{sl_prefix}mobile/") and e.endswith('.png'):
                basename = os.path.basename(e)
                m = re.match(r'^([A-Za-z0-9]+)_80_DX', basename)
                if m:
                    mobile_id_map[m.group(1)] = basename

        for slide in slides:
            sid = slide['id']
            slide_title = slide.get('title', '')
            js_path = f"{sl_prefix}html5/data/js/{sid}.js"
            if js_path not in entries:
                continue

            with zf.open(js_path) as f:
                js_content = f.read().decode("utf-8", errors="replace")

            # Find which images this slide references
            slide_images = [fname for img_id, fname in mobile_id_map.items()
                            if img_id in js_content]
            # Skip navigation/overview slides that aggregate many images
            if len(slide_images) > 2:
                continue
            best_img = max(
                slide_images,
                key=lambda x: int(re.search(r'DX(\d+)', x).group(1))
                              if re.search(r'DX(\d+)', x) else 0,
                default=None
            )

            # Extract readable text strings
            strings = re.findall(r'"([^"]{15,})"', js_content)
            seen, readable = set(), []
            for s in strings:
                if (s not in seen
                        and re.search(r'[a-zA-Z ]{8,}', s)
                        and not re.search(r'[{}<>;()\[\]\\%]', s)
                        and ' ' in s
                        and not _STORYLINE_NOISE.search(s)):
                    seen.add(s)
                    readable.append(s)

            # "Meet X, [Role]" strings → promote to full heading; rest → description
            meet_title = next(
                (s for s in readable if re.match(r'^Meet\s+', s, re.IGNORECASE)), None)
            display_title = meet_title or slide_title

            desc_parts = [s for s in readable
                          if s.lower() != slide_title.lower()
                          and s != meet_title
                          and len(s) > 25][:2]
            description = ' '.join(desc_parts)

            result.append({
                'tab_label': slide_title,    # short name used as tab button label
                'title': display_title,      # full heading shown inside the tab
                'description': description,
                'image': best_img,
            })

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Solution fragment renderer (used to collect blocks after a quiz into a
# "Solution" accordion without duplicating the main rendering logic)
# ─────────────────────────────────────────────────────────────────────────────

_carousel_counter = [0]


def _next_carousel_id():
    _carousel_counter[0] += 1
    return f'carousel-{_carousel_counter[0]}'


def _render_carousel_html(slides):
    """Build {carousel} snippet HTML from a list of (title, img_html, text_html)
    tuples, matching the current `snippet--carousel` markup in
    reference/html-snippet-blocks.html exactly (including ARIA attributes) —
    not the deprecated `carousel-snippet` markup in legacy-snippet-blocks.html.
    Shared by the interactive/process carousel and multi-item image galleries."""
    carousel_id = _next_carousel_id()
    out = [f'<div class="snippet--carousel" role="region" tabindex="0" id="{carousel_id}" aria-label="Image Carousel">',
           '  <div class="carousel-container">',
           '    <div class="carousel-image-area">']
    for i, (title, img_html, text_html) in enumerate(slides):
        active = ' active' if i == 0 else ''
        hidden = 'false' if i == 0 else 'true'
        out.append(f'      <div class="carousel-item{active}" role="tabpanel" aria-labelledby="tab-{i}" aria-hidden="{hidden}">')
        if title:
            out.append(f'        <h3>{title}</h3>')
        out.append('        <figure class="carousel-image-wrapper">')
        if img_html:
            out.append(f'          {img_html}')
        out.append('        </figure>')
        out.append('        <div class="carousel-text-wrapper">')
        if text_html:
            out.append(f'          <p>{text_html}</p>')
        out.append('        </div>')
        out.append('      </div>')
    out.append('    </div>')
    out.append('    <div class="carousel-controls">')
    out.append(f'      <button class="carousel-button prev-button" style="visibility:hidden" aria-label="Previous slide" aria-controls="{carousel_id}">')
    out.append('        <span class="material-symbols-outlined">keyboard_arrow_left</span>')
    out.append('      </button>')
    out.append(f'      <button class="carousel-button next-button" style="visibility:visible" aria-label="Next slide" aria-controls="{carousel_id}">')
    out.append('        <span class="material-symbols-outlined">keyboard_arrow_right</span>')
    out.append('      </button>')
    out.append('    </div>')
    out.append('    <div class="carousel-indicators" role="tablist"></div>')
    out.append('  </div>')
    out.append('</div>')
    return out


def _render_video_embed(items, fallback_title=""):
    """Render Rise multimedia/embed items into video <figure><iframe> HTML
    (Wistia or generic iframe). Shared by the main block renderer and the
    Solution-accordion fragment renderer."""
    out = []
    for item in items:
        embed = item.get('media', {}).get('embed', {})
        if not embed:
            continue
        embed_src_raw = embed.get('src', '') or embed.get('originalUrl', '')
        orig_url = embed.get('originalUrl', '')
        vid_title = embed.get('title', '') or fallback_title

        # Extract Wistia ID robustly:
        # Format 1 — src/originalUrl is a full iframe HTML string
        # Format 2 — originalUrl is a plain https://…/medias/XXXXX URL
        wistia_match = re.search(r'wistia\.net/embed/iframe/([a-zA-Z0-9]+)', embed_src_raw)
        if not wistia_match and orig_url and '<iframe' not in orig_url:
            wistia_match = re.search(r'/medias/([a-zA-Z0-9]+)', orig_url)

        if wistia_match:
            wistia_id = wistia_match.group(1)
            out.append(
                f'<figure>'
                f'<div class="wistia_video_foam_dummy" data-source-container-id="" '
                f'style="border:0px;display:block;height:0px;margin:0px;padding:0px;'
                f'position:static;visibility:hidden;width:auto"></div>'
                f'<iframe src="https://fast.wistia.net/embed/iframe/{wistia_id}?videoFoam=true" '
                f'title="{vid_title}" allow="autoplay; fullscreen" frameborder="0" '
                f'scrolling="no" name="wistia_embed" allowfullscreen="" '
                f'width="100%" height="400"></iframe></figure>'
            )
        else:
            # Non-Wistia: extract src from the HTML string or use orig_url directly
            m = re.search(r'src="([^"]+)"', embed_src_raw)
            src = m.group(1) if m else (orig_url if '<iframe' not in orig_url else '')
            if src:
                out.append(
                    f'<figure><iframe src="{src}" title="{vid_title}" '
                    f'allow="autoplay; fullscreen" frameborder="0" scrolling="no" '
                    f'allowfullscreen width="100%" height="400"></iframe></figure>'
                )
    return out


def _render_solution_fragment(block, target, source):
    """Render one block into `target` (list of HTML strings) for a Solution accordion."""
    b_type = block.get('type', '')
    variant = block.get('variant', '')
    items = block.get('items', [])

    if b_type == 'text' and variant == 'paragraph':
        for item in items:
            p = clean_html(item.get('paragraph', ''))
            if p:
                target.append(p)
        return

    if b_type == 'text' and variant == 'note':
        for item in items:
            p = clean_html(item.get('paragraph', ''))
            title_raw = item.get('title') or item.get('heading') or ''
            title_clean = re.sub(r'<\/?(?:p|h\d|strong|b)[^>]*>', '',
                                 clean_html(title_raw)).strip()
            if title_clean:
                target.append('<div class="infobox-container"><div class="infobox-note">'
                              '<div class="infobox-iconContainer"><em class="icon-info"></em></div>'
                              '<div class="infobox-content">'
                              f'<div class="infobox-title">{title_clean}</div>'
                              f'<div class="infobox-text">{p}</div>'
                              '</div></div></div>')
            else:
                target.append('<div class="infobox-container"><div class="infobox-note">'
                              '<div class="infobox-iconContainer"><em class="icon-info"></em></div>'
                              f'<div class="infobox-text">{p}</div>'
                              '</div></div>')
        return

    if b_type == 'text' and variant in ('a', 'b', 'd'):
        for item in items:
            p = clean_html(item.get('paragraph', ''))
            target.append(f'<div class="snippet block-statement__quote top">{p}</div>')
        return

    if b_type == 'text' and variant in ('heading', 'subheading', 'heading paragraph', 'subheading paragraph'):
        for item in items:
            raw_h = item.get('heading', '')
            p = clean_html(item.get('paragraph', ''))
            if raw_h:
                clean_h = re.sub(r'<\/?(?:p|strong|b)[^>]*>', '', clean_html(raw_h)).strip()
                tag = 'h2' if 'heading' in variant and 'sub' not in variant else 'h3'
                if clean_h:
                    target.append(f'<{tag}>{clean_h}</{tag}>')
            if p:
                target.append(p)
        return

    if b_type == 'image' and variant in ('full', 'hero', 'centered'):
        if variant == 'centered' and len(items) > 1:
            slides = [('', get_image_html(item), clean_html(item.get('caption', '')))
                      for item in items]
            target.extend(_render_carousel_html(slides))
            return
        for item in items:
            img_html = get_image_html(item)
            caption = clean_html(item.get('caption', ''))
            if img_html:
                target.append(f'<p>{img_html}</p>')
            if caption:
                target.append(caption)
        return

    if b_type == 'image' and variant == 'text aside':
        for idx, item in enumerate(items):
            paragraph = item.get('paragraph') or ''
            if idx > 0 and not clean_html(paragraph).strip():
                continue
            img_html = get_image_html(item)
            text_content = clean_html(paragraph or item.get('caption') or '')
            if idx == 0:
                target.append('<div class="inttSnippet" style="display:inline-block;">'
                              f'<div class="inttImageContainer left"><p>{img_html}</p></div>')
                if text_content:
                    target.append(text_content)
                target.append('</div>')
            else:
                target.append(f'<p>{img_html}</p>')
                if text_content:
                    target.append(text_content)
        return

    if b_type == 'interactive' and variant == 'accordion':
        for item in items:
            title = clean_html(item.get('title', ''))
            desc = clean_html(item.get('description', ''))
            img_html = get_image_html(item)
            title_clean = re.sub(r'<\/?(?:p|h\d)[^>]*>', '', title).strip()
            content = (f'<p>{img_html}</p>' if img_html else '') + desc
            target.append('<div class="accordion-wrapper2">'
                          f'<button class="accordion-label2">'
                          f'<span class="accordion-title">{title_clean}</span>'
                          f'<em class="icon-navigateright"></em></button>'
                          f'<div class="accordion-content">{content}</div>'
                          '</div>')
        return

    if b_type == 'list':
        target.append('<ol class="list-circles">')
        for item in items:
            p = re.sub(r'<\/?p[^>]*>', '', clean_html(item.get('paragraph', ''))).strip()
            target.append(f'<li>{p}</li>')
        target.append('</ol>')
        return

    if b_type == 'quote' and variant == 'c':
        for item in items:
            name = clean_html(item.get('name', ''))
            p = clean_html(item.get('paragraph', ''))
            avatar_node = item.get('avatar')
            avatar = get_image_html(avatar_node) if isinstance(avatar_node, dict) else ''
            target.append('<div class="quote-cont">'
                          f'{p}<div class="quote-person">')
            if avatar:
                target.append(f'<p>{avatar}</p>')
            target.append(f'<div class="quote-cite"><p>{name}</p></div></div></div>')
        return

    if b_type == 'divider' and variant == 'divider':
        target.append('<hr class="blue-line-separator">')
        return

    if b_type == 'multimedia' and variant == 'embed':
        target.extend(_render_video_embed(items, ''))
        return

    # Fallback: extract whatever text/images are present
    for item in items:
        img = get_image_html(item)
        if img:
            target.append(f'<p>{img}</p>')
        if 'heading' in item:
            h = clean_html(item['heading'])
            if h:
                target.append(h)
        if 'paragraph' in item:
            p = clean_html(item['paragraph'])
            if p:
                target.append(p)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1: Extract HTML + JSON payload from Rise data
# ─────────────────────────────────────────────────────────────────────────────

def extract_html(source, output_dir):
    """
    Parse a Rise zip (or runtime-data.js file), produce an HTML preview and a
    Thought Industries API payload (JSON).  Both are written into output_dir.
    Returns (payload_dict, payload_path).

    source: path to a .zip Rise export  OR  path to a runtime-data.js file
    output_dir: directory for all outputs (created if absent)
    """
    os.makedirs(output_dir, exist_ok=True)

    # Extract assets when given a zip directly
    if source.lower().endswith(".zip"):
        extract_assets_from_zip(source, output_dir)

    data = load_runtime_data(source)
    course_title = data.get('course', {}).get('title', 'Course Export')
    safe_title = re.sub(r'[^\w\s-]', '', course_title).strip().replace(' ', '_')
    output_file = os.path.join(output_dir, f"{safe_title}.html" if safe_title else "course_output.html")

    lessons = data.get('course', {}).get('lessons', [])
    course_desc_raw = data.get('course', {}).get('description', '').strip()
    course_desc_html = clean_html(course_desc_raw) if course_desc_raw else ''

    html = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        f"  <title>{course_title}</title>",
        "</head>",
        "<body>",
        f"  <h1>{course_title}</h1>"
    ]
    if course_desc_html:
        html.append(f'  {course_desc_html}')
        html.append('  <hr class="blue-line-separator">')

    ti_payload = {
        "title": course_title.strip(),
        "sections": [{"title": course_title.strip(), "lessons": []}]
    }
    current_lesson = None

    for lesson in lessons:
        lesson_title = to_title_case(lesson.get('title', 'Untitled Lesson').strip())
        lesson_type = lesson.get('type', '')

        if lesson_type == 'section':
            current_lesson = {"title": lesson_title, "topics": []}
            ti_payload["sections"][0]["lessons"].append(current_lesson)
            html.append(f"  <h2>Section: {lesson_title}</h2>")
            html.append("  <hr/>")
            continue

        if current_lesson is None:
            current_lesson = {"title": "Default Lesson", "topics": []}
            ti_payload["sections"][0]["lessons"].append(current_lesson)

        start_idx = len(html)
        html.append(f"  <h1>{lesson_title}</h1>")
        divider_counter = 1
        blocks = lesson.get('items', [])

        # Pre-pass: for each quiz, collect the block indices that immediately
        # follow it (up to the next quiz or numbered divider) — these become
        # the "Solution" accordion content.
        solution_of = {}  # bi -> [sol_bi, ...]
        for _bi, _blk in enumerate(blocks):
            if _blk.get('type') == 'knowledgeCheck':
                _sol, _j = [], _bi + 1
                while _j < len(blocks):
                    _bt = blocks[_j].get('type', '')
                    _bv = blocks[_j].get('variant', '')
                    if (_bt == 'knowledgeCheck'
                            or (_bt == 'divider' and _bv == 'numbered divider')):
                        break
                    if not (_bt == 'divider' and _bv == 'continue'):
                        _sol.append(_j)
                    _j += 1
                if _sol:
                    solution_of[_bi] = _sol
        sol_block_set = {idx for idxs in solution_of.values() for idx in idxs}

        for bi, block in enumerate(blocks):
            b_type = block.get('type', '')
            variant = block.get('variant', '')
            items = block.get('items', [])
            if bi in sol_block_set:
                continue

            # ── Dividers ──────────────────────────────────────────────────────

            # continue = Rise navigation button; no content equivalent in TI
            if b_type == 'divider' and variant == 'continue':
                continue

            # Numbered divider → {dividernumber}
            if b_type == 'divider' and variant == 'numbered divider':
                item_text = ''
                if items:
                    raw = (items[0].get('paragraph') or items[0].get('description')
                           or items[0].get('title') or '')
                    item_text = clean_html(raw)
                html.append('  <div class="divider-wrapper">')
                html.append('    <div class="divider-line">')
                html.append(f'      <div class="divider-number">{divider_counter}</div>')
                html.append('    </div>')
                if item_text:
                    html.append(f'    <p>{item_text}</p>')
                html.append('  </div>')
                divider_counter += 1
                continue

            # Plain divider → {bluelineseparator}
            if b_type == 'divider' and variant == 'divider':
                html.append('  <hr class="blue-line-separator">')
                continue

            # ── Text variants ─────────────────────────────────────────────────

            # Note / callout → {infobox} / {infobox with title}
            if b_type == 'text' and variant == 'note':
                for item in items:
                    p = clean_html(item.get('paragraph', ''))
                    title_raw = item.get('title') or item.get('heading') or ''
                    title_clean = re.sub(r'<\/?(?:p|h\d|strong|b)[^>]*>', '',
                                         clean_html(title_raw)).strip()
                    if title_clean:
                        html.append('  <div class="infobox-container"><div class="infobox-note">')
                        html.append('    <div class="infobox-iconContainer"><em class="icon-info"></em></div>')
                        html.append('    <div class="infobox-content">')
                        html.append(f'      <div class="infobox-title">{title_clean}</div>')
                        html.append(f'      <div class="infobox-text">{p}</div>')
                        html.append('    </div></div></div>')
                    else:
                        html.append('  <div class="infobox-container"><div class="infobox-note">')
                        html.append('    <div class="infobox-iconContainer"><em class="icon-info"></em></div>')
                        html.append(f'    <div class="infobox-text">{p}</div>')
                        html.append('  </div></div>')
                continue

            # Impact text variants (a, b, d) → {block-statement__quote}
            if b_type == 'text' and variant in ('a', 'b', 'd'):
                for item in items:
                    p = clean_html(item.get('paragraph', ''))
                    html.append('  <div class="snippet block-statement__quote top">')
                    html.append(f'      {p}')
                    html.append('  </div>')
                continue

            # Regular paragraph
            if b_type == 'text' and variant == 'paragraph':
                for item in items:
                    p = clean_html(item.get('paragraph', ''))
                    if p:
                        html.append(f'  {p}')
                continue

            # Heading / subheading (text only)
            if b_type == 'text' and variant in ('heading', 'subheading'):
                for item in items:
                    raw = clean_html(item.get('heading', ''))
                    clean = re.sub(r'<\/?(?:p|strong|b)[^>]*>', '', raw).strip()
                    if clean:
                        tag = 'h2' if variant == 'heading' else 'h3'
                        html.append(f"  <{tag}>{clean}</{tag}>")
                continue

            # Heading + paragraph
            if b_type == 'text' and variant == 'heading paragraph':
                for item in items:
                    raw_h = item.get('heading', '')
                    p = clean_html(item.get('paragraph', ''))
                    if raw_h:
                        clean_h = re.sub(r'<\/?(?:p|strong|b)[^>]*>', '',
                                         clean_html(raw_h)).strip()
                        if clean_h:
                            html.append(f"  <h2>{clean_h}</h2>")
                    if p:
                        html.append(f"  {p}")
                continue

            # Subheading + paragraph
            if b_type == 'text' and variant == 'subheading paragraph':
                for item in items:
                    raw_h = item.get('heading', '')
                    p = clean_html(item.get('paragraph', ''))
                    if raw_h:
                        clean_h = re.sub(r'<\/?(?:p|strong|b)[^>]*>', '',
                                         clean_html(raw_h)).strip()
                        if clean_h:
                            html.append(f"  <h3>{clean_h}</h3>")
                    if p:
                        html.append(f"  {p}")
                continue

            # ── Image variants ────────────────────────────────────────────────

            # Full-width image
            if b_type == 'image' and variant == 'full':
                for item in items:
                    img_html = get_image_html(item)
                    caption = clean_html(item.get('caption', ''))
                    if img_html:
                        html.append(f'  <p>{img_html}</p>')
                    if caption:
                        html.append(f'  {caption}')
                continue

            # Hero image (may contain multiple slides)
            if b_type == 'image' and variant == 'hero':
                for item in items:
                    img_html = get_image_html(item)
                    caption = clean_html(item.get('caption', ''))
                    if img_html:
                        html.append(f'  <p>{img_html}</p>')
                    if caption:
                        html.append(f'  {caption}')
                continue

            # Centered image (gallery family). Multiple items = image gallery
            # -> render as a {carousel} snippet; a single item stays a plain image.
            if b_type == 'image' and variant == 'centered':
                if len(items) > 1:
                    slides = [('', get_image_html(item), clean_html(item.get('caption', '')))
                              for item in items]
                    html.extend(_render_carousel_html(slides))
                else:
                    for item in items:
                        img_html = get_image_html(item)
                        caption = clean_html(item.get('caption', ''))
                        if img_html:
                            html.append(f'  <p>{img_html}</p>')
                        if caption:
                            html.append(f'  {caption}')
                continue

            # Two-column images → pair of imagetextleft / imagetextright
            if b_type == 'image' and variant == 'two column':
                for i, item in enumerate(items):
                    img_html = get_image_html(item)
                    caption = clean_html(item.get('caption', ''))
                    align = 'left' if i % 2 == 0 else 'right'
                    html.append('  <div class="inttSnippet" style="display:inline-block;">')
                    html.append(f'    <div class="inttImageContainer {align}"><p>{img_html}</p></div>')
                    if caption:
                        html.append(f'    {caption}')
                    html.append('  </div>')
                continue

            # Text overlay → {textonimage}: .text nested inside .image
            if b_type == 'image' and variant == 'text overlay':
                for item in items:
                    img_html = get_image_html(item)
                    caption = clean_html(item.get('caption', ''))
                    html.append('  <div class="textonimage full">')
                    html.append('    <div class="image">')
                    html.append(f'      <p>{img_html}</p>')
                    if caption:
                        html.append(f'      <div class="text">{caption}</div>')
                    html.append('    </div>')
                    html.append('  </div>')
                continue

            # Text aside → {imagetextleft} (left-aligned by default)
            if b_type == 'image' and variant == 'text aside':
                for idx, item in enumerate(items):
                    paragraph = item.get('paragraph') or ''
                    if idx > 0 and not clean_html(paragraph).strip():
                        # Caption-only trailing item — Rise authoring artifact, drop it.
                        continue
                    img_html = get_image_html(item)
                    text_content = clean_html(paragraph or item.get('caption') or '')
                    if idx == 0:
                        html.append('  <div class="inttSnippet" style="display:inline-block;">')
                        html.append(f'    <div class="inttImageContainer left"><p>{img_html}</p></div>')
                        if text_content:
                            html.append(f'    {text_content}')
                        html.append('  </div>')
                    else:
                        html.append(f'  <p>{img_html}</p>')
                        if text_content:
                            html.append(f'  {text_content}')
                continue

            # ── Interactive variants ───────────────────────────────────────────

            # Button / button stack → {externalsource}
            if b_type == 'interactive' and variant in ('button', 'button stack'):
                for item in items:
                    label = clean_html(item.get('label', 'Go to guide'))
                    desc = clean_html(item.get('description', ''))
                    title_text = re.sub(r'<\/?(?:p|strong|b)[^>]*>', '', desc).strip()
                    dest = item.get('destination', '#')
                    html.append('  <div class="extSource">')
                    html.append('   <div class="extSource-wrap">')
                    html.append('    <div class="extSource-text">')
                    html.append(f'      <p class="extSource-title">{title_text}</p>')
                    html.append('    </div>')
                    html.append(f'    <a href="{dest}">{label}</a>')
                    html.append('   </div>')
                    html.append('  </div>')
                continue

            # Flashcards → {accordion} (no images)
            if b_type == 'interactive' and variant == 'flashcard':
                for item in items:
                    front = item.get('front', {})
                    back = item.get('back', {})
                    front_desc = clean_html(front.get('description', 'Flashcard Front'))
                    back_desc = clean_html(back.get('description', 'Flashcard Back'))
                    front_clean = re.sub(r'<\/?(?:p|h\d)[^>]*>', '', front_desc).strip()
                    html.append('  <div class="accordion-wrapper2">')
                    html.append(f'      <button class="accordion-label2"><span class="accordion-title">{front_clean}</span><em class="icon-navigateright"></em></button>')
                    html.append(f'      <div class="accordion-content">{back_desc}</div>')
                    html.append('  </div>')
                continue

            # Sorting activity → grouped lists, one per pile (no images; drag-and-drop original)
            if b_type == 'interactive' and variant == 'sorting':
                piles = block.get('piles', [])
                for pile in piles:
                    pile_title = clean_html(pile.get('title', ''))
                    pile_title = re.sub(r'<\/?(?:p|h\d)[^>]*>', '', pile_title).strip()
                    pile_items = [item for item in items if item.get('pileId') == pile.get('id')]
                    if pile_title:
                        html.append(f'  <h3>{pile_title}</h3>')
                    html.append('  <ul>')
                    for item in pile_items:
                        title = clean_html(item.get('title', ''))
                        title = re.sub(r'<\/?(?:p|h\d)[^>]*>', '', title).strip()
                        html.append(f'    <li>{title}</li>')
                    html.append('  </ul>')
                continue

            # Labeled graphic → {imagetextleft} with bullet points
            if b_type == 'interactive' and variant == 'labeledgraphic':
                main_img_html = get_image_html(block)
                html.append('  <div class="inttSnippet" style="display:inline-block;">')
                html.append(f'    <div class="inttImageContainer left"><p>{main_img_html}</p></div>')
                html.append('    <ul>')
                for item in items:
                    title = clean_html(item.get('title', ''))
                    desc = clean_html(item.get('description', ''))
                    html.append(f'      <li><strong>{title}</strong>: {desc}</li>')
                html.append('    </ul>')
                html.append('  </div>')
                continue

            # Accordions → {accordion}
            if b_type == 'interactive' and variant == 'accordion':
                for item in items:
                    title = clean_html(item.get('title', ''))
                    desc = clean_html(item.get('description', ''))
                    img_html = get_image_html(item)
                    title_clean = re.sub(r'<\/?(?:p|h\d)[^>]*>', '', title).strip()
                    content = (f'<p>{img_html}</p>' if img_html else '') + desc
                    html.append('  <div class="accordion-wrapper2">')
                    html.append(f'      <button class="accordion-label2"><span class="accordion-title">{title_clean}</span><em class="icon-navigateright"></em></button>')
                    html.append(f'      <div class="accordion-content">{content}</div>')
                    html.append('  </div>')
                continue

            # Tabs → {tabs}
            if b_type == 'interactive' and variant == 'tabs':
                html.append('  <div class="snippet--tabs-wrapper">')
                html.append('    <div class="snippet--tabs-top-wrapper">')
                html.append('      <div class="snippet--tabs-buttons-wrapper" role="tablist">')
                for i, item in enumerate(items):
                    title_clean = re.sub(r'<\/?(?:p|h\d)[^>]*>', '',
                                         clean_html(item.get('title', ''))).strip()
                    cls = ' class="tab-selected"' if i == 0 else ''
                    html.append(f'        <button{cls} role="tab"><span class="tab-title">{title_clean}</span></button>')
                html.append('      </div>')
                html.append('    </div>')
                for i, item in enumerate(items):
                    desc = clean_html(item.get('description', ''))
                    cls = " tab-content-show" if i == 0 else ""
                    html.append(f'    <div class="snippet--tabs-content{cls}" role="tabpanel">')
                    html.append(f'        {desc}')
                    html.append('    </div>')
                html.append('  </div>')
                continue

            # Process → {carousel}  (outer: carousel-snippet, items in carousel-image-area)
            if b_type == 'interactive' and variant == 'process':
                slides = []
                for item in items:
                    img_html = get_image_html(item)
                    title = clean_html(item.get('title', ''))
                    desc = clean_html(item.get('description', ''))
                    slides.append((title, img_html, desc))
                html.extend(_render_carousel_html(slides))
                continue

            # Timeline → {tabs}
            if b_type == 'interactive' and variant == 'timeline':
                html.append('  <div class="snippet--tabs-wrapper">')
                html.append('    <div class="snippet--tabs-top-wrapper">')
                html.append('      <div class="snippet--tabs-buttons-wrapper" role="tablist">')
                for i, item in enumerate(items):
                    label = item.get('date') or item.get('title') or f"Step {i + 1}"
                    cls = ' class="tab-selected"' if i == 0 else ''
                    html.append(f'        <button{cls} role="tab"><span class="tab-title">{label}</span></button>')
                html.append('      </div>')
                html.append('    </div>')
                for i, item in enumerate(items):
                    img_html = get_image_html(item)
                    desc = clean_html(item.get('description', ''))
                    title = item.get('title', '')
                    cls = " tab-content-show" if i == 0 else ""
                    html.append(f'    <div class="snippet--tabs-content{cls}" role="tabpanel">')
                    if title:
                        html.append(f'        <h3>{title}</h3>')
                    if img_html:
                        html.append(f'        <p>{img_html}</p>')
                    if desc:
                        html.append(f'        {desc}')
                    html.append('    </div>')
                html.append('  </div>')
                continue

            # Storyline → carousel (built from per-slide JS data)
            # Falls back to iframe placeholder when zip data isn't available.
            if b_type == 'interactive' and variant == 'storyline':
                for item in items:
                    media = item.get('media', {}).get('storyline', {})
                    sl_title = media.get('title', 'Interactive Activity')
                    src = media.get('src', '')
                    sl_meta = media.get('meta', {})
                    sl_slides = sl_meta.get('slides', [])
                    content_prefix = media.get('contentPrefix', '')

                    carousel_data = []
                    if sl_slides and content_prefix and source.lower().endswith('.zip'):
                        try:
                            carousel_data = _extract_storyline_slides(
                                source, content_prefix, sl_slides)
                        except Exception as e:
                            print(f"    Warning: Storyline carousel extraction failed: {e}")

                    if carousel_data:
                        # Render as tabs — tab_label on the button, full title + content inside
                        html.append('  <div class="snippet--tabs-wrapper">')
                        html.append('    <div class="snippet--tabs-top-wrapper">')
                        html.append('      <div class="snippet--tabs-buttons-wrapper" role="tablist">')
                        for i, slide in enumerate(carousel_data):
                            cls = ' class="tab-selected"' if i == 0 else ''
                            html.append(f'        <button{cls} role="tab">'
                                        f'<span class="tab-title">{slide["tab_label"]}</span></button>')
                        html.append('      </div>')
                        html.append('    </div>')
                        for i, slide in enumerate(carousel_data):
                            img_tag = (
                                f'<img src="PENDING_CDN_UPLOAD" '
                                f'data-local="assets/{slide["image"]}" '
                                f'alt="{slide["title"]}" />'
                                if slide['image'] else ''
                            )
                            cls = " tab-content-show" if i == 0 else ""
                            html.append(f'    <div class="snippet--tabs-content{cls}" role="tabpanel">')
                            html.append(f'        <h3>{slide["title"]}</h3>')
                            if img_tag:
                                html.append(f'        <p>{img_tag}</p>')
                            if slide['description']:
                                html.append(f'        <p>{slide["description"]}</p>')
                            html.append('    </div>')
                        html.append('  </div>')
                    else:
                        assets_path = f"assets/{src}" if src else "assets/story.html"
                        html.append(
                            f'  <figure>'
                            f'<iframe src="PENDING_STORYLINE_UPLOAD" data-local="{assets_path}" '
                            f'title="{sl_title}" allow="autoplay; fullscreen" frameborder="0" '
                            f'scrolling="no" allowfullscreen width="100%" height="600">'
                            f'</iframe></figure>'
                        )
                continue

            # ── Knowledge checks / Quizzes ────────────────────────────────────

            if b_type == 'knowledgeCheck' or b_type in ('MULTIPLE_CHOICE', 'MULTIPLE_RESPONSE', 'MATCHING', 'quiz'):
                quiz_items = items if b_type == 'knowledgeCheck' else [block]
                for item in quiz_items:
                    q = clean_html(item.get('title', ''))
                    if not q:
                        continue
                    image_html = get_image_html(item)

                    # Feedback: prefer specific correct/incorrect; fall back to "any response" feedback
                    def _inline_text(raw):
                        """Strip block tags and decode entities for use in an inline context."""
                        if not raw:
                            return ''
                        t = re.sub(r'<[^>]+>', ' ', clean_html(raw))
                        import html as _h; t = _h.unescape(t)
                        t = re.sub(r'&nbsp;', ' ', t)
                        return re.sub(r'\s+', ' ', t).strip()

                    fb_any = _inline_text(item.get('feedback', ''))
                    fb_correct = _inline_text(item.get('feedbackCorrect', '')) or fb_any
                    fb_incorrect = _inline_text(item.get('feedbackIncorrect', ''))

                    html.append('  <div class="onpagequizz">')
                    html.append(f'  <p class="question">{q}</p>')
                    if image_html:
                        html.append(f'  <p>{image_html}</p>')
                    html.append('  <ul class="answers">')
                    answers = item.get('answers', [])
                    correct_ids = item.get('corrects', [])
                    if not correct_ids and 'correct' in item:
                        correct_ids = [item.get('correct')]
                    for ans in answers:
                        ans_text = clean_html(ans.get('title', ''))
                        if item.get('type') == 'MATCHING' and 'matchTitle' in ans:
                            ans_text += ' - ' + clean_html(ans.get('matchTitle', ''))
                        ans_id = ans.get('id')
                        is_correct = ans_id in correct_ids or ans.get('correct') is True
                        btn_cls = "answer correct" if is_correct else "answer"
                        res_attrs = ' id="result" class="correct"' if is_correct else ' id="result"'
                        res_icon = "icon-check" if is_correct else "icon-delete"
                        feedback = fb_correct if is_correct else fb_incorrect
                        if is_correct and feedback:
                            res_text = f"Correct &mdash; {feedback}"
                        elif not is_correct and feedback:
                            res_text = f"Incorrect &mdash; {feedback}"
                        else:
                            res_text = "Correct" if is_correct else "Incorrect"
                        html.append(f'      <li><button class="{btn_cls}">{ans_text}</button>')
                        html.append(f'      <div{res_attrs}><p><em class="{res_icon}"></em>{res_text}</p></div></li>')
                    html.append('  </ul></div>')
                # Wrap any following solution blocks in a "Solution" accordion
                if bi in solution_of:
                    _sol_buf = []
                    for _sol_bi in solution_of[bi]:
                        _render_solution_fragment(blocks[_sol_bi], _sol_buf, source)
                    if _sol_buf:
                        _sol_content = '\n'.join(_sol_buf)
                        html.append('  <div class="accordion-wrapper2">')
                        html.append('      <button class="accordion-label2">'
                                    '<span class="accordion-title">Solution</span>'
                                    '<em class="icon-navigateright"></em></button>')
                        html.append(f'      <div class="accordion-content">{_sol_content}</div>')
                        html.append('  </div>')
                continue

            # ── Multimedia ────────────────────────────────────────────────────

            # Video embed (Wistia or generic iframe)
            if b_type == 'multimedia' and variant == 'embed':
                fallback_title = re.sub(
                    r'\s*\[\d+[:\d]*(?:\s*min(?:s)?)?\]\s*$', '', lesson_title).strip()
                html.extend(_render_video_embed(items, fallback_title))
                continue

            # File attachment → {externalsource} download link
            # PDF/docx files are extracted to assets/ but need manual CDN upload.
            if b_type == 'multimedia' and variant == 'attachment':
                for item in items:
                    att = item.get('media', {}).get('attachment', {})
                    raw_key = urllib.parse.unquote(att.get('key', ''))
                    basename = os.path.basename(raw_key) or raw_key
                    label = re.sub(r'\.[^.]+$', '', basename)  # strip extension for title
                    html.append('  <div class="extSource">')
                    html.append('   <div class="extSource-wrap">')
                    html.append('    <div class="extSource-text">')
                    html.append(f'      <p class="extSource-title">{label}</p>')
                    html.append('    </div>')
                    html.append(f'    <a href="PENDING_ATTACHMENT_UPLOAD" '
                                f'data-local="assets/{basename}">Download</a>')
                    html.append('   </div>')
                    html.append('  </div>')
                continue

            # Audio → <audio> tag referencing extracted asset
            if b_type == 'multimedia' and variant == 'audio':
                for item in items:
                    audio = item.get('media', {}).get('audio', {})
                    filename = (audio.get('originalUrl')
                                or urllib.parse.unquote(audio.get('key', ''))
                                or 'audio.mp3')
                    basename = os.path.basename(filename)
                    caption = clean_html(item.get('caption', ''))
                    html.append('  <figure>')
                    html.append(f'    <audio controls src="PENDING_CDN_UPLOAD" data-local="assets/{basename}">')
                    html.append('      Your browser does not support the audio element.')
                    html.append('    </audio>')
                    if caption:
                        html.append(f'    <figcaption>{caption}</figcaption>')
                    html.append('  </figure>')
                continue

            # ── Lists ──────────────────────────────────────────────────────────

            if b_type == 'list':
                html.append('  <ol class="list-circles">')
                for item in items:
                    p = clean_html(item.get('paragraph', ''))
                    p = re.sub(r'<\/?p[^>]*>', '', p).strip()
                    html.append(f'    <li>{p}</li>')
                html.append('  </ol>')
                continue

            # ── Quote ──────────────────────────────────────────────────────────

            if b_type == 'quote' and variant == 'c':
                for item in items:
                    name = clean_html(item.get('name', ''))
                    p = clean_html(item.get('paragraph', ''))
                    avatar_node = item.get('avatar')
                    avatar = get_image_html(avatar_node) if isinstance(avatar_node, dict) else ''
                    html.append('  <div class="quote-cont">')
                    html.append(f'      {p}')
                    html.append('      <div class="quote-person">')
                    if avatar:
                        html.append(f'          <p>{avatar}</p>')
                    html.append(f'          <div class="quote-cite"><p>{name}</p></div>')
                    html.append('      </div>')
                    html.append('  </div>')
                continue

            # ── Fallback (unknown blocks) ──────────────────────────────────────
            for item in items:
                img = get_image_html(item)
                if img:
                    html.append(f'  <p>{img}</p>')
                if 'heading' in item:
                    h = clean_html(item['heading'])
                    if h:
                        html.append(f"  {h}")
                if 'paragraph' in item:
                    p = clean_html(item['paragraph'])
                    if p:
                        html.append(f"  {p}")

        html.append("  <hr/>")

        lesson_html = "\n".join(html[start_idx:])
        lesson_html = re.sub(r'<p>\s*(?:<br\s*/?>)?\s*</p>', '', lesson_html)

        current_lesson["topics"].append({
            "title": lesson_title,
            "type": "text",
            "body": lesson_html
        })

    # Prepend cover page as first topic of first lesson in TI payload
    if course_desc_html:
        cover_topic = {"title": "Welcome", "type": "text", "body": course_desc_html}
        for sec in ti_payload.get("sections", []):
            for les in sec.get("lessons", []):
                les["topics"].insert(0, cover_topic)
                break
            break

    html.append("</body>")
    html.append("</html>")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(html))
    print(f"  HTML preview   → {output_file}")

    payload_filename = f"{safe_title}_payload.json" if safe_title else "course_payload.json"
    output_payload_file = os.path.join(output_dir, payload_filename)
    with open(output_payload_file, 'w', encoding='utf-8') as f:
        json.dump(ti_payload, f, indent=2)
    print(f"  TI payload     → {output_payload_file}")

    return ti_payload, output_payload_file

# ─────────────────────────────────────────────────────────────────────────────
# Phase 1b: Extract a reviewable Word (.docx) doc from Rise data, with every
# block labeled with its intended TI snippet. Parallel/additive to extract_html
# — parses the same Rise source data directly, does not round-trip through HTML.
# ─────────────────────────────────────────────────────────────────────────────

def get_image_path(node, assets_dir):
    """Return (local_file_path_or_None, alt_text) for a Rise image node, resolved
    against assets_dir. Mirrors get_image_html but for docx embedding."""
    if not isinstance(node, dict):
        return None, ''
    img_data = node.get('media', {}).get('image', {})
    if not img_data:
        return None, ''
    filename = urllib.parse.unquote(img_data.get('crushedKey', '')) or img_data.get('originalUrl') or ''
    basename = os.path.basename(filename)
    path = os.path.join(assets_dir, basename) if basename else None
    if path and not os.path.isfile(path):
        path = None

    raw_alt = (node.get('caption') or node.get('heading') or
               node.get('title') or node.get('paragraph') or "")
    if raw_alt:
        alt = _plain_text(raw_alt)
    else:
        alt = re.sub(r'\.[^.]+$', '', basename).replace('-', ' ').replace('_', ' ')
    return path, alt


def _plain_text(raw):
    """Strip tags/entities from a fragment for plain-text use (labels, titles)."""
    if not raw:
        return ''
    import html as _html
    t = re.sub(r'<[^>]+>', ' ', clean_html(raw))
    t = _html.unescape(t)
    t = t.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', t).strip()


def _video_urls(items):
    """Resolve Rise multimedia/embed items to plain video URLs (Wistia or generic).
    Docx can't embed a live player, so Solution/video blocks show '[Video: <url>]'."""
    urls = []
    for item in items:
        embed = item.get('media', {}).get('embed', {})
        if not embed:
            continue
        embed_src_raw = embed.get('src', '') or embed.get('originalUrl', '')
        orig_url = embed.get('originalUrl', '')
        wistia_match = re.search(r'wistia\.net/embed/iframe/([a-zA-Z0-9]+)', embed_src_raw)
        if not wistia_match and orig_url and '<iframe' not in orig_url:
            wistia_match = re.search(r'/medias/([a-zA-Z0-9]+)', orig_url)
        if wistia_match:
            urls.append(f'https://fast.wistia.net/embed/iframe/{wistia_match.group(1)}')
        else:
            m = re.search(r'src="([^"]+)"', embed_src_raw)
            src = m.group(1) if m else (orig_url if '<iframe' not in orig_url else '')
            if src:
                urls.append(src)
    return urls


class _IndentedContainer:
    """Proxy that forwards add_paragraph/add_table to a real container (Document
    or a docx _Cell) while indenting every paragraph it creates. Used to visually
    group Solution-accordion content under its quiz without a full sub-document."""
    def __init__(self, real_container, indent_inches=0.4):
        self._c = real_container
        self._indent = Inches(indent_inches)

    def add_paragraph(self, text='', style=None):
        p = self._c.add_paragraph(text, style=style)
        p.paragraph_format.left_indent = self._indent
        return p

    def add_table(self, rows, cols):
        return self._c.add_table(rows, cols)


def _add_run_with_formatting(paragraph, soup_node, bold=False, italic=False, underline=False):
    """Recursively walk a BeautifulSoup node, adding runs to `paragraph` with
    bold/italic/underline accumulated from strong/b, em/i, u ancestor tags."""
    for child in soup_node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text:
                run = paragraph.add_run(text)
                run.bold = bold
                run.italic = italic
                run.underline = underline
        else:
            name = (child.name or '').lower()
            if name == 'br':
                paragraph.add_run().add_break()
                continue
            b2 = bold or name in ('strong', 'b')
            i2 = italic or name in ('em', 'i')
            u2 = underline or name == 'u'
            _add_run_with_formatting(paragraph, child, b2, i2, u2)


def _add_html_table(container, table_soup):
    rows = table_soup.find_all('tr')
    if not rows:
        return
    ncols = max(len(r.find_all(['td', 'th'])) for r in rows)
    if ncols == 0:
        return
    tbl = container.add_table(rows=0, cols=ncols)
    try:
        tbl.style = 'Light Grid Accent 1'
    except Exception:
        pass
    for r in rows:
        cells = r.find_all(['td', 'th'])
        row_cells = tbl.add_row().cells
        for i, cell in enumerate(cells):
            if i >= ncols:
                break
            p = row_cells[i].paragraphs[0]
            _add_run_with_formatting(p, cell)
            if cell.name == 'th':
                for run in p.runs:
                    run.bold = True


def _add_html_content(container, raw_html, bullet_style='List Bullet'):
    """Render a clean_html'd fragment into docx paragraphs, preserving bold/
    italic/underline and list/heading/table structure."""
    if not raw_html or not raw_html.strip():
        return
    soup = BeautifulSoup(raw_html, 'html.parser')

    for table in soup.find_all('table'):
        _add_html_table(container, table)
        table.extract()

    block_tags = {'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'div'}
    top_nodes = [n for n in soup.contents if not (isinstance(n, NavigableString) and not n.strip())]
    if not top_nodes:
        return
    if not any(getattr(n, 'name', None) in block_tags for n in top_nodes):
        p = container.add_paragraph()
        _add_run_with_formatting(p, soup)
        return

    def _walk(nodes):
        for node in nodes:
            if isinstance(node, NavigableString):
                if node.strip():
                    container.add_paragraph(node.strip())
                continue
            name = (node.name or '').lower()
            if name in ('ul', 'ol'):
                for li in node.find_all('li', recursive=False):
                    p = container.add_paragraph(style=bullet_style)
                    _add_run_with_formatting(p, li)
                continue
            if name == 'li':
                p = container.add_paragraph(style=bullet_style)
                _add_run_with_formatting(p, node)
                continue
            if re.match(r'^h[1-6]$', name or ''):
                level = int(name[1])
                p = container.add_paragraph(style=f'Heading {min(level + 2, 4)}')
                _add_run_with_formatting(p, node)
                continue
            if name in ('p', 'div'):
                p = container.add_paragraph()
                _add_run_with_formatting(p, node)
                continue
            _walk(list(node.children))

    _walk(top_nodes)


def _add_snippet_label(container, label):
    p = container.add_paragraph()
    run = p.add_run(f'Snippet: {label}')
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x80, 0x80, 0x80)
    return p


def _add_note_label(container, text):
    """Unlabeled-snippet callout (e.g. sorting activities with no TI equivalent)."""
    p = container.add_paragraph()
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(9)
    run.font.color.rgb = RGBColor(0x99, 0x33, 0x00)
    return p


def _add_image(container, path, alt, max_width_inches=5.5):
    if not path:
        if alt:
            p = container.add_paragraph()
            p.add_run(f'[Missing image asset: {alt}]').italic = True
        return
    p = container.add_paragraph()
    run = p.add_run()
    if path.lower().endswith('.svg'):
        p.add_run(f'[SVG asset — not previewable in Word, see assets/{os.path.basename(path)}]').italic = True
        if alt:
            cap = container.add_paragraph()
            cap_run = cap.add_run(alt)
            cap_run.italic = True
            cap_run.font.size = Pt(9)
        return
    try:
        run.add_picture(path, width=Inches(max_width_inches))
    except Exception:
        # python-docx's image scanner rejects some valid formats it can't parse
        # headers for (e.g. progressive JPEGs, which Rise exports routinely).
        # Re-encode through Pillow to a baseline format it does recognize.
        if not _PIL_AVAILABLE:
            p.add_run(f'[Image could not be embedded: {os.path.basename(path)}]')
            return
        try:
            import io
            with _PILImage.open(path) as im:
                buf = io.BytesIO()
                im.convert('RGB').save(buf, format='PNG')
                buf.seek(0)
            run.add_picture(buf, width=Inches(max_width_inches))
        except Exception as e2:
            p.add_run(f'[Image could not be embedded: {os.path.basename(path)} ({e2})]')
            return
    if alt:
        cap = container.add_paragraph()
        cap_run = cap.add_run(alt)
        cap_run.italic = True
        cap_run.font.size = Pt(9)


def _render_docx_block(container, block, bi, blocks, solution_of, dc,
                        output_dir, assets_dir, source, lesson_title, in_solution=False):
    """Render one Rise block into `container` (a Document, or an _IndentedContainer
    for Solution-accordion content). Mirrors extract_html's dispatch conditions
    exactly, labeling every block that maps to a real TI snippet. `dc` is a
    single-item list holding the numbered-divider counter (mutated in place).
    """
    b_type = block.get('type', '')
    variant = block.get('variant', '')
    items = block.get('items', [])

    # ── Dividers ──────────────────────────────────────────────────────────
    if b_type == 'divider' and variant == 'continue':
        return

    if b_type == 'divider' and variant == 'numbered divider':
        item_text = ''
        if items:
            raw = (items[0].get('paragraph') or items[0].get('description')
                   or items[0].get('title') or '')
            item_text = clean_html(raw)
        _add_snippet_label(container, 'Numbered Divider')
        p = container.add_paragraph()
        p.add_run(f'{dc[0]}.').bold = True
        dc[0] += 1
        _add_html_content(container, item_text)
        return

    if b_type == 'divider' and variant == 'divider':
        _add_snippet_label(container, 'Blue Line Separator')
        return

    # ── Text variants ─────────────────────────────────────────────────────
    if b_type == 'text' and variant == 'note':
        for item in items:
            p_html = clean_html(item.get('paragraph', ''))
            title_clean = _plain_text(item.get('title') or item.get('heading') or '')
            _add_snippet_label(container, 'Info Box')
            if title_clean:
                p = container.add_paragraph()
                p.add_run(title_clean).bold = True
            _add_html_content(container, p_html)
        return

    if b_type == 'text' and variant in ('a', 'b', 'd'):
        for item in items:
            p_html = clean_html(item.get('paragraph', ''))
            _add_snippet_label(container, 'Quote / Statement Callout')
            _add_html_content(container, p_html)
        return

    if b_type == 'text' and variant == 'paragraph':
        for item in items:
            p_html = clean_html(item.get('paragraph', ''))
            _add_html_content(container, p_html)
        return

    if b_type == 'text' and variant in ('heading', 'subheading'):
        for item in items:
            clean_h = _plain_text(item.get('heading', ''))
            if clean_h:
                style = 'Heading 3' if variant == 'heading' else 'Heading 4'
                container.add_paragraph(clean_h, style=style)
        return

    if b_type == 'text' and variant in ('heading paragraph', 'subheading paragraph'):
        for item in items:
            clean_h = _plain_text(item.get('heading', ''))
            p_html = clean_html(item.get('paragraph', ''))
            if clean_h:
                style = 'Heading 3' if 'sub' not in variant else 'Heading 4'
                container.add_paragraph(clean_h, style=style)
            _add_html_content(container, p_html)
        return

    # ── Image variants ───────────────────────────────────────────────────
    if b_type == 'image' and variant in ('full', 'hero'):
        for item in items:
            path, alt = get_image_path(item, assets_dir)
            _add_image(container, path, alt)
            _add_html_content(container, clean_html(item.get('caption', '')))
        return

    if b_type == 'image' and variant == 'centered':
        if len(items) > 1:
            _add_snippet_label(container, 'Carousel')
            for i, item in enumerate(items):
                path, alt = get_image_path(item, assets_dir)
                container.add_paragraph(f'Slide {i + 1}', style='Heading 4')
                _add_image(container, path, alt)
                _add_html_content(container, clean_html(item.get('caption', '')))
        else:
            for item in items:
                path, alt = get_image_path(item, assets_dir)
                _add_image(container, path, alt)
                _add_html_content(container, clean_html(item.get('caption', '')))
        return

    if b_type == 'image' and variant == 'two column':
        _add_snippet_label(container, 'Image + Text (Side-by-Side)')
        for item in items:
            path, alt = get_image_path(item, assets_dir)
            _add_image(container, path, alt)
            _add_html_content(container, clean_html(item.get('caption', '')))
        return

    if b_type == 'image' and variant == 'text overlay':
        _add_snippet_label(container, 'Text on Image')
        for item in items:
            path, alt = get_image_path(item, assets_dir)
            _add_image(container, path, alt)
            _add_html_content(container, clean_html(item.get('caption', '')))
        return

    if b_type == 'image' and variant == 'text aside':
        _add_snippet_label(container, 'Image + Text (Side-by-Side)')
        for idx, item in enumerate(items):
            paragraph = item.get('paragraph') or ''
            if idx > 0 and not clean_html(paragraph).strip():
                continue
            path, alt = get_image_path(item, assets_dir)
            _add_image(container, path, alt)
            text_content = clean_html(paragraph or item.get('caption') or '')
            _add_html_content(container, text_content)
        return

    # ── Interactive variants ─────────────────────────────────────────────
    if b_type == 'interactive' and variant in ('button', 'button stack'):
        _add_snippet_label(container, 'External Source Link')
        for item in items:
            label = _plain_text(item.get('label', 'Go to guide'))
            desc = _plain_text(item.get('description', ''))
            dest = item.get('destination', '#')
            if desc:
                container.add_paragraph(desc)
            container.add_paragraph(f'{label} -> {dest}')
        return

    if b_type == 'interactive' and variant == 'flashcard':
        _add_snippet_label(container, 'Accordion')
        for item in items:
            front = item.get('front', {})
            back = item.get('back', {})
            front_clean = _plain_text(front.get('description', 'Flashcard Front'))
            back_html = clean_html(back.get('description', 'Flashcard Back'))
            p = container.add_paragraph()
            p.add_run(f'Q: {front_clean}').bold = True
            _add_html_content(container, back_html)
        return

    if b_type == 'interactive' and variant == 'sorting':
        _add_note_label(container, 'No TI snippet — Rise drag-and-drop sorting activity, '
                                    'shown below as a grouped list for reviewer reference.')
        piles = block.get('piles', [])
        for pile in piles:
            pile_title = _plain_text(pile.get('title', ''))
            pile_items = [item for item in items if item.get('pileId') == pile.get('id')]
            if pile_title:
                container.add_paragraph(pile_title, style='Heading 4')
            for item in pile_items:
                container.add_paragraph(_plain_text(item.get('title', '')), style=bullet_style_const)
        return

    if b_type == 'interactive' and variant == 'labeledgraphic':
        _add_snippet_label(container, 'Image + Text (Side-by-Side)')
        path, alt = get_image_path(block, assets_dir)
        _add_image(container, path, alt)
        for item in items:
            title = _plain_text(item.get('title', ''))
            desc = clean_html(item.get('description', ''))
            p = container.add_paragraph(style='List Bullet')
            p.add_run(f'{title}: ').bold = True
            _add_run_with_formatting(p, BeautifulSoup(desc, 'html.parser'))
        return

    if b_type == 'interactive' and variant == 'accordion':
        _add_snippet_label(container, 'Accordion')
        for item in items:
            title_clean = _plain_text(item.get('title', ''))
            desc = clean_html(item.get('description', ''))
            path, alt = get_image_path(item, assets_dir)
            p = container.add_paragraph()
            p.add_run(f'Q: {title_clean}').bold = True
            if path:
                _add_image(container, path, alt)
            _add_html_content(container, desc)
        return

    if b_type == 'interactive' and variant == 'tabs':
        _add_snippet_label(container, 'Tabs')
        for item in items:
            title_clean = _plain_text(item.get('title', ''))
            desc = clean_html(item.get('description', ''))
            container.add_paragraph(title_clean, style='Heading 4')
            _add_html_content(container, desc)
        return

    if b_type == 'interactive' and variant == 'process':
        _add_snippet_label(container, 'Carousel')
        for i, item in enumerate(items):
            path, alt = get_image_path(item, assets_dir)
            title = _plain_text(item.get('title', ''))
            desc = clean_html(item.get('description', ''))
            container.add_paragraph(title or f'Slide {i + 1}', style='Heading 4')
            _add_image(container, path, alt)
            _add_html_content(container, desc)
        return

    if b_type == 'interactive' and variant == 'timeline':
        _add_snippet_label(container, 'Tabs')
        for i, item in enumerate(items):
            label = item.get('date') or item.get('title') or f'Step {i + 1}'
            path, alt = get_image_path(item, assets_dir)
            desc = clean_html(item.get('description', ''))
            container.add_paragraph(_plain_text(label), style='Heading 4')
            _add_image(container, path, alt)
            _add_html_content(container, desc)
        return

    if b_type == 'interactive' and variant == 'storyline':
        for item in items:
            media = item.get('media', {}).get('storyline', {})
            sl_title = media.get('title', 'Interactive Activity')
            sl_meta = media.get('meta', {})
            sl_slides = sl_meta.get('slides', [])
            content_prefix = media.get('contentPrefix', '')

            carousel_data = []
            if sl_slides and content_prefix and source.lower().endswith('.zip'):
                try:
                    carousel_data = _extract_storyline_slides(source, content_prefix, sl_slides)
                except Exception as e:
                    print(f"    Warning: Storyline carousel extraction failed: {e}")

            if carousel_data:
                _add_snippet_label(container, 'Carousel')
                for slide in carousel_data:
                    container.add_paragraph(slide['title'], style='Heading 4')
                    if slide['image']:
                        _add_image(container, os.path.join(assets_dir, slide['image']), slide['title'])
                    if slide['description']:
                        container.add_paragraph(slide['description'])
            else:
                _add_note_label(container, f"Embedded Storyline interactive ('{sl_title}') — "
                                            "no slide data extracted; needs manual review in Rise.")
        return

    # ── Knowledge checks / Quizzes ───────────────────────────────────────
    if b_type == 'knowledgeCheck' or b_type in ('MULTIPLE_CHOICE', 'MULTIPLE_RESPONSE', 'MATCHING', 'quiz'):
        quiz_items = items if b_type == 'knowledgeCheck' else [block]
        for item in quiz_items:
            q = _plain_text(item.get('title', ''))
            if not q:
                continue
            _add_snippet_label(container, 'On-Page Quiz')
            p = container.add_paragraph()
            p.add_run(f'Q: {q}').bold = True
            path, alt = get_image_path(item, assets_dir)
            _add_image(container, path, alt)

            fb_any = _plain_text(item.get('feedback', ''))
            fb_correct = _plain_text(item.get('feedbackCorrect', '')) or fb_any
            fb_incorrect = _plain_text(item.get('feedbackIncorrect', ''))

            answers = item.get('answers', [])
            correct_ids = item.get('corrects', [])
            if not correct_ids and 'correct' in item:
                correct_ids = [item.get('correct')]
            for ans in answers:
                ans_text = _plain_text(ans.get('title', ''))
                if item.get('type') == 'MATCHING' and 'matchTitle' in ans:
                    ans_text += ' - ' + _plain_text(ans.get('matchTitle', ''))
                ans_id = ans.get('id')
                is_correct = ans_id in correct_ids or ans.get('correct') is True
                feedback = fb_correct if is_correct else fb_incorrect
                mark = '[Correct]' if is_correct else '[Incorrect]'
                p = container.add_paragraph(style='List Bullet')
                p.add_run(f'{mark} {ans_text}')
                if feedback:
                    fb_p = container.add_paragraph()
                    fb_run = fb_p.add_run(feedback)
                    fb_run.italic = True
        if bi in solution_of and not in_solution:
            _add_snippet_label(container, 'Solution (Accordion)')
            sol_container = _IndentedContainer(container)
            for sol_bi in solution_of[bi]:
                _render_docx_block(sol_container, blocks[sol_bi], sol_bi, blocks, {}, dc,
                                    output_dir, assets_dir, source, lesson_title, in_solution=True)
        return

    # ── Multimedia ────────────────────────────────────────────────────────
    if b_type == 'multimedia' and variant == 'embed':
        _add_snippet_label(container, 'Video Embed')
        urls = _video_urls(items)
        for url in urls:
            container.add_paragraph(f'[Video: {url}]')
        return

    # Natively-uploaded video (as opposed to an embedded Wistia/iframe link)
    if b_type == 'multimedia' and variant == 'video':
        _add_snippet_label(container, 'Video Embed')
        for item in items:
            video = item.get('media', {}).get('video', {})
            filename = (video.get('originalUrl') or urllib.parse.unquote(video.get('key', '')) or 'video.mp4')
            basename = os.path.basename(filename)
            caption = clean_html(item.get('caption', ''))
            container.add_paragraph(f'[Video: assets/{basename}]')
            _add_html_content(container, caption)
        return

    if b_type == 'multimedia' and variant == 'attachment':
        _add_snippet_label(container, 'External Source Link (Download)')
        for item in items:
            att = item.get('media', {}).get('attachment', {})
            raw_key = urllib.parse.unquote(att.get('key', ''))
            basename = os.path.basename(raw_key) or raw_key
            label = re.sub(r'\.[^.]+$', '', basename)
            container.add_paragraph(f'{label} (asset: {basename})')
        return

    if b_type == 'multimedia' and variant == 'audio':
        _add_snippet_label(container, 'Audio Embed')
        for item in items:
            audio = item.get('media', {}).get('audio', {})
            filename = (audio.get('originalUrl') or urllib.parse.unquote(audio.get('key', '')) or 'audio.mp3')
            basename = os.path.basename(filename)
            caption = clean_html(item.get('caption', ''))
            container.add_paragraph(f'[Audio: {basename}]')
            _add_html_content(container, caption)
        return

    # ── Lists ─────────────────────────────────────────────────────────────
    if b_type == 'list':
        _add_snippet_label(container, 'Formatted List')
        for item in items:
            p_html = re.sub(r'<\/?p[^>]*>', '', clean_html(item.get('paragraph', ''))).strip()
            p = container.add_paragraph(style='List Number')
            _add_run_with_formatting(p, BeautifulSoup(p_html, 'html.parser'))
        return

    # ── Quote ─────────────────────────────────────────────────────────────
    if b_type == 'quote' and variant in ('a', 'c'):
        _add_snippet_label(container, 'Quote with Person')
        for item in items:
            name = _plain_text(item.get('name', ''))
            p_html = clean_html(item.get('paragraph', ''))
            avatar_node = item.get('avatar')
            _add_html_content(container, p_html)
            if isinstance(avatar_node, dict):
                path, alt = get_image_path(avatar_node, assets_dir)
                _add_image(container, path, alt)
            if name:
                p = container.add_paragraph()
                p.add_run(f'— {name}').italic = True
        return

    # ── Fallback (unknown blocks) ────────────────────────────────────────
    for item in items:
        path, alt = get_image_path(item, assets_dir)
        if path:
            _add_image(container, path, alt)
        if 'heading' in item:
            h = _plain_text(item['heading'])
            if h:
                container.add_paragraph(h, style='Heading 4')
        if 'paragraph' in item:
            _add_html_content(container, clean_html(item['paragraph']))


bullet_style_const = 'List Bullet'


def extract_docx(source, output_dir):
    """
    Parse a Rise zip (or runtime-data.js file) into a reviewable Word document
    that labels every block with its intended TI snippet, for colleague review
    and rework before content is transferred to Google Docs and eventually
    re-ingested into TI. Additive/parallel to extract_html — produces no HTML
    or TI JSON payload, and does not touch that pipeline.

    source: path to a .zip Rise export OR a runtime-data.js file
    output_dir: directory for all outputs (created if absent)
    Returns the path to the generated .docx file.
    """
    if not _DOCX_AVAILABLE:
        print("The 'python-docx' library is not installed. Please run: pip install python-docx")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)

    if source.lower().endswith(".zip"):
        assets_dir = extract_assets_from_zip(source, output_dir)
    else:
        assets_dir = os.path.join(output_dir, "assets")

    data = load_runtime_data(source)
    course_title = data.get('course', {}).get('title', 'Course Export')
    safe_title = re.sub(r'[^\w\s-]', '', course_title).strip().replace(' ', '_')
    output_file = os.path.join(output_dir, f"{safe_title}.docx" if safe_title else "course_output.docx")

    lessons = data.get('course', {}).get('lessons', [])
    course_desc_raw = data.get('course', {}).get('description', '').strip()

    doc = docx.Document()
    doc.add_heading(course_title, level=1)
    if course_desc_raw:
        _add_html_content(doc, clean_html(course_desc_raw))

    block_count = 0
    for lesson in lessons:
        lesson_title = to_title_case(lesson.get('title', 'Untitled Lesson').strip())
        lesson_type = lesson.get('type', '')

        if lesson_type == 'section':
            doc.add_heading(f'Section: {lesson_title}', level=1)
            continue

        doc.add_heading(lesson_title, level=2)
        blocks = lesson.get('items', [])
        dc = [1]

        solution_of = {}
        for _bi, _blk in enumerate(blocks):
            if _blk.get('type') == 'knowledgeCheck':
                _sol, _j = [], _bi + 1
                while _j < len(blocks):
                    _bt = blocks[_j].get('type', '')
                    _bv = blocks[_j].get('variant', '')
                    if (_bt == 'knowledgeCheck'
                            or (_bt == 'divider' and _bv == 'numbered divider')):
                        break
                    if not (_bt == 'divider' and _bv == 'continue'):
                        _sol.append(_j)
                    _j += 1
                if _sol:
                    solution_of[_bi] = _sol
        sol_block_set = {idx for idxs in solution_of.values() for idx in idxs}

        for bi, block in enumerate(blocks):
            if bi in sol_block_set:
                continue
            _render_docx_block(doc, block, bi, blocks, solution_of, dc,
                                output_dir, assets_dir, source, lesson_title)
            block_count += 1

        divider_p = doc.add_paragraph()
        divider_run = divider_p.add_run('─' * 60)
        divider_run.font.color.rgb = RGBColor(0xC0, 0xC0, 0xC0)

    doc.save(output_file)
    print(f"  Word doc       -> {output_file}  ({block_count} block(s) rendered)")
    return output_file


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extract a Rise 360 zip export into a TI HTML/JSON payload or a reviewable Word doc.")
    parser.add_argument("source", help="Path to the Rise .zip export (or a runtime-data.js file).")
    parser.add_argument("--output", required=True, help="Directory to write assets/ and the output file(s) into.")
    parser.add_argument("--format", choices=["html", "docx"], default="html",
                        help="'html' (default) produces the HTML preview + TI payload JSON. "
                             "'docx' produces a reviewable Word doc only (no payload JSON, no TI push yet).")
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"ERROR: source not found: {args.source}")
        sys.exit(1)

    if args.format == "docx":
        output_file = extract_docx(args.source, args.output)
        print(f"\nDone. Hand '{output_file}' to the reviewer before continuing the migration.")
    else:
        payload, payload_path = extract_html(args.source, args.output)
        n_sections = len(payload.get("sections", []))
        n_lessons = sum(len(s.get("lessons", [])) for s in payload.get("sections", []))
        n_topics = sum(len(l.get("topics", [])) for s in payload.get("sections", []) for l in s.get("lessons", []))
        print(f"\nDone. {n_sections} section(s), {n_lessons} lesson(s), {n_topics} topic(s).")
        print(f"Payload: {payload_path}")
        print("Next: run image_uploader.py + patch_cdn_urls.py (from convert-course-to-html) "
              "to resolve PENDING_CDN_UPLOAD before pushing to TI.")


if __name__ == "__main__":
    main()
