#!/usr/bin/env python3
"""
Celonis Docs Crawler
--------------------
Reads the sidebar navigation from a Paligo-generated docs page,
extracts all linked URLs, fetches each page, and saves as .md files.

Two authentication modes (auto-detected):

  Cookie mode (recommended for Cowork / no-browser environments):
    Set CELONIS_DOCS_SESSION_COOKIE in secrets.env -- no browser needed.
    Value: sf_session=<token>  (see skill guide for how to get this)

  Playwright mode (macOS / Windows with browser):
    On first run a browser window opens for Celonaut SSO login.
    Session saved to ~/.claude/celonis_docs_session.json and reused automatically.

Usage:
    printf '<ENTRY_URL>\n<OUTPUT_PATH>\n' | python crawl_celonis_docs.py

Dependencies are auto-installed if missing.
"""

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

# -- Bootstrap dependencies -----------------------------------------------------
try:
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md
except ImportError:
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install",
        "beautifulsoup4", "markdownify",
        "--break-system-packages", "-q"
    ])
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md

try:
    import requests as _requests_lib
except ImportError:
    import subprocess
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "requests",
        "--break-system-packages", "-q"
    ])
    import requests as _requests_lib

DELAY = 0.5
DOCS_DOMAIN = "docs.celonis.com"
SESSION_FILE = Path.home() / ".claude" / "celonis_docs_session.json"


# -- Load CELONIS_DOCS_SESSION_COOKIE from secrets.env -------------------------

def _load_cookie_from_secrets() -> None:
    """If CELONIS_DOCS_SESSION_COOKIE is not already in env, try secrets.env."""
    if os.environ.get("CELONIS_DOCS_SESSION_COOKIE"):
        return
    for path in [
        Path.cwd() / "secrets.env",
        Path.home() / ".claude" / "secrets.env",
    ]:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line.startswith("CELONIS_DOCS_SESSION_COOKIE="):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    os.environ["CELONIS_DOCS_SESSION_COOKIE"] = val
                return


_load_cookie_from_secrets()


# -- Requests-based (cookie) mode -----------------------------------------------

def _make_requests_session(cookie: str) -> _requests_lib.Session:
    s = _requests_lib.Session()
    s.headers.update({
        "Cookie": cookie,
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    })
    return s


def _requests_get_soup(session, url: str) -> BeautifulSoup | None:
    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
        if DOCS_DOMAIN not in resp.url:
            print(f"  [WARN] Redirected off docs domain -- session cookie may have expired.")
            print(f"         Refresh sf_session in secrets.env and re-run.")
            return None
        if resp.status_code != 200:
            print(f"  [ERROR] {url} returned {resp.status_code}")
            return None
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  [ERROR] {url} -- {e}")
        return None


# -- Playwright-based (SSO) mode ------------------------------------------------

def _on_docs_domain(page) -> bool:
    return DOCS_DOMAIN in urlparse(page.url).netloc


def ensure_authenticated(page, entry_url: str) -> None:
    """Go to entry_url and handle SSO redirect if needed."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

    page.goto(entry_url, wait_until="domcontentloaded", timeout=30_000)

    if not _on_docs_domain(page):
        print()
        print("+-----------------------------------------------------------------+")
        print("|  Celonaut SSO login required                                    |")
        print("|  Complete login in the browser window, then press Enter here.   |")
        print("+-----------------------------------------------------------------+")
        input("Press Enter once you are logged in... ")

        page.goto(entry_url, wait_until="domcontentloaded", timeout=30_000)
        if not _on_docs_domain(page):
            print("Still not on docs domain -- waiting for navigation...")
            try:
                page.wait_for_url(f"**{DOCS_DOMAIN}**", timeout=30_000)
            except PlaywrightTimeoutError:
                print("[ERROR] Could not reach docs domain after login. Aborting.")
                sys.exit(1)

    print("[INFO] Authenticated -- proceeding with crawl.")


def load_session_state():
    if SESSION_FILE.exists():
        import json
        try:
            data = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            print(f"[INFO] Loading saved session from {SESSION_FILE}")
            return data
        except Exception:
            print("[WARN] Could not parse session file -- starting fresh.")
    return None


def save_session_state(context) -> None:
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    context.storage_state(path=str(SESSION_FILE))
    print(f"[INFO] Session saved to {SESSION_FILE}")


def _playwright_get_soup(page, url: str) -> BeautifulSoup | None:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        if not _on_docs_domain(page):
            print(f"  [WARN] Redirected away from docs domain -- session may have expired.")
            return None
        return BeautifulSoup(page.content(), "html.parser")
    except Exception as e:
        print(f"  [ERROR] {url} - {e}")
        return None


# -- Sidebar / URL extraction ---------------------------------------------------

def find_sidebar(soup: BeautifulSoup):
    el = soup.find(id="nav-site-sidebar")
    if el:
        return el, "id=nav-site-sidebar"
    el = soup.find("ul", class_=lambda c: c and "nav-site-sidebar" in c)
    if el:
        return el, "ul.nav-site-sidebar"
    el = soup.find(class_=lambda c: c and "toc" in c and "nav" in c)
    if el:
        return el, f"class={el.get('class')}"
    for tag in ["aside", "nav"]:
        el = soup.find(tag)
        if el and el.find("a", class_=lambda c: c and "topic-link" in c):
            return el, f"<{tag}> with topic-links"
    el = soup.find("a", class_=lambda c: c and "topic-link" in c)
    if el:
        parent = el.find_parent(["ul", "nav", "aside", "div"])
        if parent:
            return parent, f"parent of topic-link anchors ({parent.name})"
    return None, None


def extract_sidebar_urls(soup: BeautifulSoup, entry_url: str) -> list[str]:
    sidebar, strategy = find_sidebar(soup)
    if not sidebar:
        print("[WARN] Could not find sidebar nav.")
        return []
    print(f"[INFO] Found sidebar via: {strategy}")

    entry_filename = entry_url.rstrip("/").split("/")[-1]
    anchor = sidebar.find("a", href=lambda h: h and entry_filename in h)
    if anchor:
        section_li = anchor.find_parent("li")
        title = anchor.get_text(strip=True)
        print(f"[INFO] Scoping to section: '{title}'")
        search_root = section_li if section_li else sidebar
    else:
        print("[WARN] Could not scope -- crawling entire sidebar.")
        search_root = sidebar

    urls = []
    seen = set()
    for a in search_root.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#"):
            continue
        abs_url = urljoin(entry_url, href).split("#")[0]
        if urlparse(abs_url).netloc != urlparse(entry_url).netloc:
            continue
        if abs_url not in seen:
            seen.add(abs_url)
            urls.append(abs_url)
    return urls


# -- Markdown conversion --------------------------------------------------------

def extract_main_content(soup: BeautifulSoup):
    for selector in ["main", "article", "[role='main']", ".content", "#content", "body"]:
        el = soup.select_one(selector)
        if el:
            return el
    return soup


def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    stem = Path(path).stem
    stem = re.sub(r"[^\w\-]", "_", stem)
    return stem or "index"


def page_title(soup: BeautifulSoup) -> str:
    tag = soup.find("h1") or soup.find("title")
    return tag.get_text(strip=True) if tag else "Untitled"


def save_markdown(url: str, soup: BeautifulSoup, out_dir: Path) -> None:
    content_el = extract_main_content(soup)
    title = page_title(soup)
    raw_md = md(str(content_el), heading_style="ATX", strip=["script", "style", "nav", "footer"])
    clean_md = re.sub(r"\n{3,}", "\n\n", raw_md).strip()
    header = f"---\nsource: {url}\ntitle: {title}\n---\n\n# {title}\n\n"
    final = header + clean_md

    slug = slug_from_url(url)
    out_path = out_dir / f"{slug}.md"
    counter = 1
    while out_path.exists():
        out_path = out_dir / f"{slug}_{counter}.md"
        counter += 1

    out_path.write_text(final, encoding="utf-8")
    print(f"  OK  {out_path.name}  ({len(final):,} chars)")


# -- Shared crawl loop ----------------------------------------------------------

def _crawl(get_soup_fn, entry_url: str, output_dir: Path) -> int:
    """Fetch sidebar URLs and save each as .md. get_soup_fn(url) -> BeautifulSoup|None."""
    entry_soup = get_soup_fn(entry_url)
    if not entry_soup:
        print("[ERROR] Could not fetch entry page.")
        sys.exit(1)

    urls = extract_sidebar_urls(entry_soup, entry_url)
    print(f"Found {len(urls)} pages in sidebar.\n")

    if entry_url not in urls:
        urls.insert(0, entry_url)

    saved = 0
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}")
        soup = get_soup_fn(url)
        if soup:
            save_markdown(url, soup, output_dir)
            saved += 1
        time.sleep(DELAY)
    return saved


# -- Main -----------------------------------------------------------------------

def main():
    entry_url = input().strip()
    output_dir = Path(input().strip())
    output_dir.mkdir(parents=True, exist_ok=True)

    cookie = os.environ.get("CELONIS_DOCS_SESSION_COOKIE", "").strip()

    # -- Cookie / requests mode -------------------------------------------------
    if cookie:
        print("[INFO] Cookie mode -- using CELONIS_DOCS_SESSION_COOKIE (no browser needed).")
        session = _make_requests_session(cookie)

        resp = session.get(entry_url, timeout=15, allow_redirects=True)
        if DOCS_DOMAIN not in resp.url:
            print("[ERROR] Session cookie is not authenticated or has expired.")
            print("  Refresh your sf_session cookie and update CELONIS_DOCS_SESSION_COOKIE in secrets.env.")
            print("  See the fetch-celonis-docs skill guide for instructions.")
            sys.exit(1)

        saved = _crawl(lambda url: _requests_get_soup(session, url), entry_url, output_dir)
        print(f"\nDone. {saved} file(s) saved to {output_dir}/")
        return

    # -- Playwright mode --------------------------------------------------------
    playwright_available = False
    try:
        from playwright.sync_api import sync_playwright
        playwright_available = True
    except ImportError:
        pass

    if not playwright_available:
        print("[ERROR] Playwright is not available and CELONIS_DOCS_SESSION_COOKIE is not set.")
        print()
        print("  Option A -- Cookie mode (works everywhere, recommended for Cowork):")
        print("    1. Log in to docs.celonis.com in your browser.")
        print("    2. Open DevTools (F12) > Application > Cookies > docs.celonis.com")
        print("    3. Copy the Value of the 'sf_session' cookie.")
        print("    4. Add to secrets.env:  CELONIS_DOCS_SESSION_COOKIE=sf_session=<value>")
        print()
        print("  Option B -- Playwright mode (macOS / Windows):")
        print("    pip install playwright && python -m playwright install chromium")
        sys.exit(1)

    session_state = load_session_state()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)

        if session_state:
            context = browser.new_context(storage_state=session_state)
        else:
            context = browser.new_context()

        page = context.new_page()

        try:
            ensure_authenticated(page, entry_url)
            save_session_state(context)
            saved = _crawl(lambda url: _playwright_get_soup(page, url), entry_url, output_dir)
        finally:
            browser.close()

    print(f"\nDone. {saved} file(s) saved to {output_dir}/")


if __name__ == "__main__":
    main()
