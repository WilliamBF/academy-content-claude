#!/usr/bin/env python3
"""
content-creation-plugin first-time setup helper
-------------------------------------------------
Checks for a secrets.env file and prints the template if one is missing.
Run once after installing the plugin to confirm credentials are in place.

Claude Code automatically sets CONTENT_CREATION_PLUGIN_ROOT when the plugin
is loaded — no manual settings.json editing is needed.
"""

import pathlib

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent


def main():
    plugin_creds = PLUGIN_ROOT / "secrets.env"
    home_creds = pathlib.Path.home() / ".claude" / "secrets.env"

    print("-" * 61)
    print("content-creation-plugin — credentials check")
    print("-" * 61)

    if plugin_creds.exists():
        print(f"OK  secrets.env found at {plugin_creds}")
        print("    All TI-connected skills will use it automatically.")
        print("    This location persists across Cowork sessions and plugin updates.")
    elif home_creds.exists():
        print(f"OK  secrets.env found at {home_creds}")
        print("    Note: home directory is ephemeral in Cowork / container environments.")
        print("    For a persistent setup, copy secrets.env to the plugin install folder:")
        print(f"    {plugin_creds}")
    else:
        print("MISSING  No secrets.env found.")
        print()
        print("Option 1 — Plugin install folder (recommended, persists in Cowork):")
        print()
        print(f"  {plugin_creds}")
        print()
        print("  TI_BASE_URL=https://academy.celonis.com")
        print("  TI_API_KEY=<your api key>")
        print("  TI_LEARNER_EMAIL=claude.uploader@celonis.com")
        print("  TI_LEARNER_PASSWORD=<password>")
        print()
        print("  # Optional: plugin auto-update via GitHub Releases")
        print("  PLUGIN_UPDATE_GITHUB_REPO=<owner/repo>")
        print("  PLUGIN_UPDATE_GITHUB_TOKEN=<fine-grained-pat-with-contents-read>")
        print()
        print("Option 2 — No file (Claude Code settings.json, any environment):")
        print()
        print("  Add these variables to settings.json under the \"env\" key:")
        print("    TI_BASE_URL, TI_API_KEY, TI_LEARNER_EMAIL, TI_LEARNER_PASSWORD")
        print()
        print("Option 3 — Workspace root (per-project, works everywhere):")
        print()
        print("  Place secrets.env in the folder you open as your workspace.")

    print("-" * 61)


if __name__ == "__main__":
    main()
