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
    workspace_creds = PLUGIN_ROOT / "secrets.env"
    home_creds = pathlib.Path.home() / ".claude" / "secrets.env"

    print("-" * 61)
    print("content-creation-plugin — credentials check")
    print("-" * 61)

    if workspace_creds.exists():
        print(f"OK  secrets.env found at {workspace_creds}")
        print("    All TI-connected skills will use it automatically.")
    elif home_creds.exists():
        print(f"OK  secrets.env found at {home_creds}")
        print("    Note: this location does not persist in Cowork / container")
        print("    environments. Copy to your workspace root if you use Cowork.")
    else:
        print("MISSING  No secrets.env found.")
        print()
        print("Create one at your workspace root:")
        print()
        print(f"  {PLUGIN_ROOT / 'secrets.env'}")
        print()
        print("  TI_BASE_URL=https://academy.celonis.com")
        print("  TI_API_KEY=<your api key>")
        print("  TI_LEARNER_EMAIL=claude.uploader@celonis.com")
        print("  TI_LEARNER_PASSWORD=<password>")
        print()
        print("  # Optional: plugin auto-update via GitHub Releases")
        print("  PLUGIN_UPDATE_GITHUB_REPO=<owner/repo>")
        print("  PLUGIN_UPDATE_GITHUB_TOKEN=<fine-grained-pat-with-contents-read>")

    print("-" * 61)


if __name__ == "__main__":
    main()
