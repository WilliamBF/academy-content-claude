"""
patch_cdn_urls.py
-----------------
After running image_uploader.py, use this script to replace all
PENDING_CDN_UPLOAD placeholders in a TI HTML file with the real CDN URLs.

It reads the JSON map produced by image_uploader.py, then for every entry:
  - Finds <img src="PENDING_CDN_UPLOAD" ... data-local="04_Assets/imageN.png">
  - Replaces src with the CDN URL
  - Removes the data-local attribute
  - Removes the <!-- IMAGE: ... needs TI CDN upload --> comment above the tag

Usage:
    python patch_cdn_urls.py <html_file> <cdn_map.json> [--dry-run]

Options:
    --dry-run    Print a summary of what would change without writing the file
    --backup     Keep a .bak copy of the original HTML (default: True)

Example:
    python patch_cdn_urls.py courses/data-visualization/03_HTML/intro-data-viz.html \\
                             courses/data-visualization/05_LMS_Sync/cdn_map.json
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def log(msg: str):
    print(f"[patch_cdn_urls] {msg}", flush=True)


def patch_html(html: str, cdn_map: dict[str, str]) -> tuple[str, list[str], list[str]]:
    """
    Replace PENDING_CDN_UPLOAD src values and clean up data-local / placeholder comments.

    Returns:
        patched_html   -- updated HTML string
        patched        -- list of filenames successfully replaced
        missing        -- filenames in HTML that had no CDN URL in the map
    """
    patched = []
    missing = []

    for filename, cdn_url in cdn_map.items():
        if not cdn_url:
            continue  # Skip failed uploads

        # Escape for regex (dots in filenames etc.)
        escaped = re.escape(filename)

        # -- 1. Replace src and remove data-local -----------------------------
        # Pattern: src="PENDING_CDN_UPLOAD" ... data-local="...filename..."
        # (attributes may appear in either order; handle both)

        # Forward order: src first, then data-local
        pattern_fwd = (
            r'src="PENDING_CDN_UPLOAD"'
            r'(\s[^>]*?)?'                        # any other attrs in between
            r'\s+data-local="[^"]*' + escaped + r'[^"]*"'
        )
        replacement_fwd = f'src="{cdn_url}"'

        new_html, n = re.subn(pattern_fwd, replacement_fwd, html)
        if n:
            html = new_html
            patched.append(filename)
            log(f"  OK {filename} -> {cdn_url[:60]}...")
        else:
            # Reverse order: data-local first, then src
            pattern_rev = (
                r'data-local="[^"]*' + escaped + r'[^"]*"'
                r'(\s[^>]*?)?'
                r'\s+src="PENDING_CDN_UPLOAD"'
            )
            replacement_rev = f'src="{cdn_url}"'
            new_html, n = re.subn(pattern_rev, replacement_rev, html)
            if n:
                html = new_html
                patched.append(filename)
                log(f"  OK {filename} (reverse attr order) -> {cdn_url[:60]}...")
            else:
                missing.append(filename)
                log(f"  ! {filename} - not found in HTML (already patched?)")

        # -- 2. Remove the <!-- IMAGE: ... needs TI CDN upload --> comment -----
        comment_pattern = r'<!--\s*IMAGE:\s*[^>]*?' + escaped + r'[^>]*?-->\s*\n?'
        html = re.sub(comment_pattern, '', html)

    return html, patched, missing


def find_remaining_pending(html: str) -> list[str]:
    """Return all data-local values still paired with PENDING_CDN_UPLOAD."""
    return re.findall(r'data-local="([^"]+)"', html)


def main():
    parser = argparse.ArgumentParser(
        description="Patch PENDING_CDN_UPLOAD placeholders in a TI HTML file using a cdn_map.json."
    )
    parser.add_argument("html_file",   help="Path to the TI HTML file to patch")
    parser.add_argument("cdn_map",     help="Path to the cdn_map.json from image_uploader.py")
    parser.add_argument("--dry-run",   action="store_true", help="Preview changes without writing")
    parser.add_argument("--no-backup", action="store_true", help="Skip .bak backup of original")
    args = parser.parse_args()

    html_path = Path(args.html_file)
    map_path  = Path(args.cdn_map)

    if not html_path.exists():
        print(f"ERROR: HTML file not found: {html_path}", file=sys.stderr)
        sys.exit(1)
    if not map_path.exists():
        print(f"ERROR: CDN map not found: {map_path}", file=sys.stderr)
        sys.exit(1)

    html = html_path.read_text(encoding="utf-8")
    with open(map_path) as f:
        cdn_map: dict = json.load(f)

    log(f"HTML file  : {html_path}")
    log(f"CDN map    : {map_path} ({len(cdn_map)} entries)")

    # Count how many PENDING placeholders exist before patching
    pending_before = html.count('src="PENDING_CDN_UPLOAD"')
    log(f"Pending before: {pending_before}")

    patched_html, patched, not_found_in_html = patch_html(html, cdn_map)

    pending_after = patched_html.count('src="PENDING_CDN_UPLOAD"')
    remaining = find_remaining_pending(patched_html)

    log(f"\n-- Summary --------------------------------------------------")
    log(f"Replaced   : {len(patched)}")
    log(f"Not found  : {len(not_found_in_html)} (already patched or different filename)")
    log(f"Still pending after patch: {pending_after}")

    if remaining:
        log(f"\nImages still needing CDN upload:")
        for r in remaining:
            log(f"  - {r}")

    if args.dry_run:
        log("\nDry run -- no files written.")
        return

    # Backup original
    if not args.no_backup:
        bak = html_path.with_suffix(html_path.suffix + ".bak")
        shutil.copy2(html_path, bak)
        log(f"\nBackup saved: {bak}")

    html_path.write_text(patched_html, encoding="utf-8")
    log(f"HTML updated: {html_path}")


if __name__ == "__main__":
    main()
