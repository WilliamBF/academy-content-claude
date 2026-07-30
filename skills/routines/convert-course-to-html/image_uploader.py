#!/usr/bin/env python3
"""
TI Image Uploader
-----------------
Uses Playwright to log into Thought Industries as the dedicated uploader account,
create a new text page in the upload course shell, upload images one by one via
the Redactor WYSIWYG editor, and collect CDN URLs.

Images remain on the platform -- no deletion. The page is saved at the end.

Produces a JSON map: { "filename.png": "https://d3i9g4671ronu3.cloudfront.net/..." }

Usage:
    python image_uploader.py <images_folder> [--output cdn_map.json] [--title "Upload batch"] [--headless] [--resume]

Credentials (resolved via lib/config.py -> secrets.env or env vars):
    TI_BASE_URL           e.g. https://academy.celonis.com
    TI_LEARNER_EMAIL      e.g. claude.uploader@celonis.com
    TI_LEARNER_PASSWORD   the uploader account password

Setup:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

# -- Bootstrap: add plugin root to path ----------------------------------------
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

from lib.config import resolve_credentials

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}

# Dedicated upload course shell -- this account only has access to this course.
UPLOAD_COURSE_URL = (
    "https://academy.celonis.com/learn/manager/course/"
    "82c68700-2c31-4ddd-9595-911fdea1b982/sections?tab=content"
)


def log(msg: str):
    print(f"[uploader] {msg}", flush=True)


def dismiss_cookies(page):
    try:
        btn = page.locator("#onetrust-reject-all-handler")
        btn.wait_for(state="visible", timeout=5000)
        btn.click()
        time.sleep(0.5)
    except Exception:
        pass


def login(page, base_url: str, email: str, password: str):
    log("Navigating to sign-in page...")
    page.goto(f"{base_url}/learn/internal_sign_in", wait_until="domcontentloaded")
    dismiss_cookies(page)
    page.fill("input[name='email'], input[type='email']", email)
    page.fill("input[name='password'], input[type='password']", password)
    page.click("input[type='submit'], button[type='submit']")
    page.wait_for_load_state("networkidle")
    dismiss_cookies(page)
    log(f"Logged in as {email}")


def navigate_to_course_manager(page):
    log("Navigating to upload course shell...")
    page.goto(UPLOAD_COURSE_URL, wait_until="networkidle")
    dismiss_cookies(page)
    time.sleep(2)


def create_text_page(page):
    """Click the round Add Page (+) button, then choose Text page type."""
    log("Creating new text page...")

    # Round + button -- identified by its sr-only label
    add_btn = page.locator("button:has(span.sr-only:text-is('Add Page'))").first
    add_btn.wait_for(state="visible", timeout=10000)
    add_btn.click()
    time.sleep(0.5)

    # Text page type -- class is stable; filter by visible label text
    text_btn = page.locator("button.new-page__button--create").filter(has_text="Text").first
    text_btn.wait_for(state="visible", timeout=10000)
    text_btn.click()
    time.sleep(2)

    log("Editor ready.")


def upload_image(page, image_path: Path) -> str | None:
    """
    Upload one image via the Redactor image toolbar button.
    Returns the CDN src URL of the uploaded image.
    """
    existing_count = page.locator("figure.redactor-uploaded-figure img").count()

    # Click the image toolbar button
    img_btn = page.locator("a.re-button[data-re-name='image']")
    img_btn.wait_for(state="visible", timeout=10000)
    img_btn.click()
    time.sleep(0.5)

    # Upload box appears -- use file-chooser interception
    upload_box = page.locator("div.upload-redactor-box")
    upload_box.wait_for(state="visible", timeout=5000)

    try:
        with page.expect_file_chooser(timeout=5000) as fc_info:
            upload_box.click()
        fc_info.value.set_files(str(image_path))
    except Exception:
        # Fallback: set files directly on a visible file input
        file_input = page.locator("input[type='file']").first
        file_input.set_input_files(str(image_path))

    # Wait for the new figure to appear in the editor
    page.wait_for_function(
        f"document.querySelectorAll('figure.redactor-uploaded-figure img').length > {existing_count}",
        timeout=30000,
    )
    time.sleep(1)

    # Extract CDN URL from the last uploaded figure
    last_img = page.locator("figure.redactor-uploaded-figure img").last
    try:
        last_img.wait_for(state="visible", timeout=5000)
        cdn_url = last_img.get_attribute("src")
        log(f"  CDN URL: {cdn_url}")
    except Exception as e:
        log(f"  WARNING: could not read CDN URL -- {e}")
        cdn_url = None

    # Move cursor past the figure so the next upload starts on a new line
    page.locator("figure.redactor-uploaded-figure").last.click()
    page.keyboard.press("ArrowDown")
    time.sleep(0.3)

    return cdn_url


def save_page(page, title: str):
    """Fill the page title input and click Save."""
    log(f"Saving page as '{title}'...")

    title_input = page.locator("div.form__input__container input[type='text']").first
    title_input.wait_for(state="visible", timeout=10000)
    title_input.fill(title)

    # Save button is below the fold -- scroll it into view first
    page.evaluate("window.scrollBy(0, 400)")
    time.sleep(0.5)

    save_btn = page.locator("button.btn--success-new:has-text('Save')").first
    save_btn.wait_for(state="visible", timeout=10000)
    save_btn.click()
    page.wait_for_load_state("networkidle")
    log("Page saved.")


def main():
    parser = argparse.ArgumentParser(
        description="Upload images to the TI CDN via the course content manager."
    )
    parser.add_argument("images_folder", help="Folder containing images to upload")
    parser.add_argument("--output", default="cdn_map.json", help="Output JSON map file (default: cdn_map.json)")
    parser.add_argument("--title", default=None, help="Title for the upload page (default: 'Image Upload YYYY-MM-DD')")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--resume", action="store_true", help="Skip images already present in --output map")
    args = parser.parse_args()

    images_folder = Path(args.images_folder)
    if not images_folder.is_dir():
        print(f"ERROR: '{images_folder}' is not a valid directory.", file=sys.stderr)
        sys.exit(1)

    creds = resolve_credentials()
    if not creds["learner_email"] or not creds["learner_password"]:
        print("ERROR: TI_LEARNER_EMAIL and TI_LEARNER_PASSWORD must be set in secrets.env.", file=sys.stderr)
        sys.exit(1)

    images = sorted(
        f for f in images_folder.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not images:
        print(f"No supported images found in '{images_folder}'.")
        sys.exit(0)

    output_path = Path(args.output)
    cdn_map: dict = {}
    if args.resume and output_path.exists():
        with open(output_path) as f:
            cdn_map = json.load(f)
        log(f"Resuming -- {len(cdn_map)} already mapped")
        images = [img for img in images if img.name not in cdn_map]

    if not images:
        log("Nothing to upload.")
        return

    page_title = args.title or f"Image Upload {date.today().isoformat()}"

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "ERROR: Playwright is not installed.\n"
            "Run: pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            login(page, creds["base_url"], creds["learner_email"], creds["learner_password"])
            navigate_to_course_manager(page)
            create_text_page(page)

            for i, image_path in enumerate(images, 1):
                log(f"[{i}/{len(images)}] {image_path.name}")
                cdn_url = upload_image(page, image_path)
                cdn_map[image_path.name] = cdn_url
                with open(output_path, "w") as f:
                    json.dump(cdn_map, f, indent=2)
                time.sleep(1)

            save_page(page, page_title)

        finally:
            browser.close()

    succeeded = sum(1 for v in cdn_map.values() if v)
    failed = sum(1 for v in cdn_map.values() if not v)
    log(f"Done. {succeeded} uploaded, {failed} failed. Map: {output_path}")


if __name__ == "__main__":
    main()
