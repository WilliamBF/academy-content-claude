#!/usr/bin/env python3
"""
Celonis Docs Search
-------------------
Finds the docs.celonis.com pages that matter for a question or topic, without
crawling the whole site, and saves them as markdown for Claude to read.

Discovery modes (combine with --fetch to download the pages):
  --url URL [URL ...]       fetch exact pages the user already pointed at
  --topic KEYWORD [...]     complete coverage of a topic: sitemap keyword
                            matches UNION the sidebar subtree of the best match
  KEYWORD [...]             plain keyword mode: fetch the top N slug matches
  --section ENTRY_URL       list (and with --fetch, download) one section's subtree

Usage:
  python search_docs.py <output_dir> --url <page_url> [<page_url> ...]
  python search_docs.py <output_dir> --topic <keyword> [<keyword> ...] [--fetch]
  python search_docs.py <output_dir> <keyword> [<keyword> ...] [--top N]
  python search_docs.py <output_dir> --section <entry_page_url> [--fetch]

Authentication (first match wins):
  1. --cookie VALUE              a cookie pasted for this run only; never written to disk
  2. CELONIS_DOCS_SESSION_COOKIE  from the environment or a secrets.env file
                                  (workspace, plugin folder, ~/.claude)
  3. The saved Playwright session (~/.claude/celonis_docs_session.json), desktop only
The cookie is the value of the `sf_session` cookie on docs.celonis.com; either
`sf_session=<value>` or the bare value is accepted.

Shares its page fetching and sidebar parsing with crawl_celonis_docs.py.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# -- Bootstrap: plugin root on the path (for lib.config) and this folder (for the crawler)
HERE = Path(__file__).resolve().parent
PLUGIN_ROOT = HERE.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
sys.path.insert(0, str(HERE))

import crawl_celonis_docs as crawler  # noqa: E402  (installs bs4/markdownify/requests if missing)
from bs4 import BeautifulSoup  # noqa: E402
from markdownify import markdownify as md  # noqa: E402

try:
    from lib.config import _load_env_file  # noqa: E402
except Exception:  # lib/ unavailable: fall back to the crawler's own (cwd + ~/.claude) lookup
    _load_env_file = None

DOCS_DOMAIN = crawler.DOCS_DOMAIN
SITEMAP_URL = f"https://{DOCS_DOMAIN}/sitemap.xml"
PLAYWRIGHT_SESSION = crawler.SESSION_FILE


def resolve_cookie(cli_cookie: str | None) -> str:
    """Return a Cookie header value like 'sf_session=<token>', or exit with guidance."""
    raw = (cli_cookie or "").strip()

    if not raw:
        if _load_env_file:
            try:
                _load_env_file(override=False)
            except Exception:
                pass
        raw = os.environ.get("CELONIS_DOCS_SESSION_COOKIE", "").strip()

    if not raw and PLAYWRIGHT_SESSION.exists():
        try:
            state = json.loads(PLAYWRIGHT_SESSION.read_text(encoding="utf-8"))
            for c in state.get("cookies", []):
                if c.get("name") == "sf_session" and "celonis" in c.get("domain", ""):
                    raw = c.get("value", "")
                    print("[INFO] Using sf_session from the saved Playwright session.")
                    break
        except Exception:
            pass

    if not raw:
        print("[ERROR] No docs.celonis.com session cookie found.")
        print("  Provide the value of the 'sf_session' cookie (browser DevTools > Application/Storage > Cookies > docs.celonis.com) by either:")
        print("    - adding CELONIS_DOCS_SESSION_COOKIE=sf_session=<value> to secrets.env, or")
        print("    - passing it for this run only with --cookie <value>")
        sys.exit(1)

    return raw if raw.startswith("sf_session=") else f"sf_session={raw}"


def fetch_sitemap_urls(session) -> list[str]:
    resp = session.get(SITEMAP_URL, timeout=30)
    if DOCS_DOMAIN not in resp.url or resp.status_code != 200:
        print(f"[ERROR] Could not fetch the sitemap (HTTP {resp.status_code}). The session cookie is probably expired; get a fresh sf_session value.")
        sys.exit(1)
    return re.findall(r"<loc>([^<]+)</loc>", resp.text)


def slug_text(url: str) -> str:
    stem = Path(urlparse(url).path).stem
    return re.sub(r"[-_]+", " ", stem).lower()


def score_url(url: str, keywords: list[str]) -> int:
    """Every keyword must appear as a whole word in the slug, otherwise 0. Requiring
    all of them keeps a phrase like 'context model' from matching every '...-model' page."""
    text = slug_text(url)
    score = 0
    for kw in keywords:
        if re.search(rf"\b{re.escape(kw.lower())}\b", text):
            score += 2
        else:
            return 0
    return score


def section_urls(session, entry_url: str) -> list[str]:
    """Every page in the entry page's sidebar subtree (uses the crawler's sidebar parser)."""
    resp = session.get(entry_url, timeout=20, allow_redirects=True)
    if DOCS_DOMAIN not in resp.url or resp.status_code != 200:
        print(f"[ERROR] Could not fetch {entry_url} (HTTP {resp.status_code}); the cookie may be expired.")
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    urls = crawler.extract_sidebar_urls(soup, entry_url)
    if entry_url not in urls:
        urls.insert(0, entry_url)
    return urls


def topic_urls(session, keywords: list[str], sitemap_urls: list[str]) -> list[str]:
    """Union of sitemap keyword matches and the sidebar subtree of the best match.
    Keyword matching misses sibling pages whose slug doesn't mention the topic
    (e.g. ccm-faq.html under the Context Model section); the subtree misses pages
    about the topic that live elsewhere. Neither alone is complete."""
    scored = sorted(((score_url(u, keywords), u) for u in sitemap_urls), key=lambda s: -s[0])
    scored = [s for s in scored if s[0] > 0]
    if not scored:
        return []
    combined = [u for _, u in scored]
    best = scored[0][1]
    print(f"[INFO] Best-matching entry page for the sidebar lookup: {best}")
    for u in section_urls(session, best):
        if u not in combined:
            combined.append(u)
    return combined


def fetch_and_save(session, url: str, out_dir: Path, used_names: dict) -> dict | None:
    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
    except Exception as e:
        print(f"  [ERROR] {url} -- {e}")
        return None
    if DOCS_DOMAIN not in resp.url:
        print("  [WARN] Redirected off the docs domain; the session cookie has probably expired.")
        return None
    if resp.status_code != 200:
        print(f"  [ERROR] HTTP {resp.status_code} for {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    title = crawler.page_title(soup)
    body = md(str(crawler.extract_main_content(soup)), heading_style="ATX",
              strip=["script", "style", "nav", "footer"])
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    slug = crawler.slug_from_url(url)
    name = slug
    n = 1
    while used_names.get(name, url) != url:  # same slug from a different URL in this run
        name = f"{slug}_{n}"
        n += 1
    used_names[name] = url

    (out_dir / f"{name}.md").write_text(
        f"---\nsource: {url}\ntitle: {title}\n---\n\n# {title}\n\n{body}", encoding="utf-8")
    return {"title": title, "source": url, "file": f"{name}.md"}


def fetch_all(session, urls: list[str], out_dir: Path) -> None:
    used: dict = {}
    saved = []
    for url in urls:
        result = fetch_and_save(session, url, out_dir, used)
        if result:
            print(f"  OK  {result['file']}  <-  {url}")
            saved.append(result)
    print(f"\nDone. {len(saved)}/{len(urls)} page(s) saved to {out_dir}/")
    for s in saved:
        print(f"  - {s['title']}: {s['file']} ({s['source']})")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Find and fetch docs.celonis.com pages for a question or topic.")
    p.add_argument("output_dir", help="Folder to write the .md files into (a scratch folder is fine)")
    p.add_argument("terms", nargs="*", help="Keywords (with --topic or on their own)")
    p.add_argument("--url", nargs="+", metavar="URL", help="Fetch these exact pages")
    p.add_argument("--section", metavar="ENTRY_URL", help="List the sidebar subtree of this page")
    p.add_argument("--topic", action="store_true", help="Complete topic coverage (keyword + sidebar subtree)")
    p.add_argument("--fetch", action="store_true", help="With --section/--topic: also download the pages")
    p.add_argument("--top", type=int, default=5, help="Plain keyword mode: pages to fetch (default 5)")
    p.add_argument("--cookie", help="sf_session cookie value for this run only (never stored)")
    return p


def main():
    args = build_parser().parse_intermixed_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    session = crawler._make_requests_session(resolve_cookie(args.cookie))

    if args.url:
        print(f"[INFO] Fetching {len(args.url)} specific page(s)...")
        fetch_all(session, args.url, out_dir)
        return

    if args.section:
        print(f"[INFO] Listing pages nested under: {args.section}")
        urls = section_urls(session, args.section)
        print(f"\n[INFO] {len(urls)} page(s) in this section (including its own page):")
        for u in urls:
            print(f"  {u}")
        if args.fetch:
            print("\n[INFO] Fetching all pages in the section...")
            fetch_all(session, urls, out_dir)
        return

    if not args.terms:
        print("[ERROR] Give at least one keyword, or use --url / --section.")
        sys.exit(1)

    print(f"[INFO] Fetching the sitemap to search for: {', '.join(args.terms)}")
    sitemap = fetch_sitemap_urls(session)
    print(f"[INFO] Sitemap has {len(sitemap)} URLs.")

    if args.topic:
        urls = topic_urls(session, args.terms, sitemap)
        if not urls:
            print("[INFO] No pages matched. Try different or broader keywords.")
            return
        print(f"\n[INFO] {len(urls)} page(s) cover this topic (keyword matches + section subtree, deduplicated):")
        for u in urls:
            print(f"  {u}")
        if args.fetch:
            print("\n[INFO] Fetching all pages for this topic...")
            fetch_all(session, urls, out_dir)
        return

    scored = sorted(((score_url(u, args.terms), u) for u in sitemap), key=lambda s: -s[0])
    scored = [s for s in scored if s[0] > 0][: args.top]
    if not scored:
        print("[INFO] No URL slugs matched. Try different or broader keywords.")
        return
    print(f"\n[INFO] Top {len(scored)} matches:")
    for score, url in scored:
        print(f"  ({score}) {url}")
    print("\n[INFO] Fetching matched pages...")
    fetch_all(session, [u for _, u in scored], out_dir)


if __name__ == "__main__":
    main()
