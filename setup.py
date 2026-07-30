#!/usr/bin/env python3
"""
content-creation-plugin setup
------------------------------
Registers CONTENT_CREATION_PLUGIN_ROOT in Claude Code's settings.json so that
skill scripts can be found regardless of the working directory.

Run once after installing the plugin:
    python setup.py

Restart Claude Code after running this script.
"""

import json
import pathlib
import sys

PLUGIN_ROOT = pathlib.Path(__file__).resolve().parent

# Claude Code stores global settings in one of these locations.
SETTINGS_CANDIDATES = [
    pathlib.Path.home() / ".claude" / "settings.json",
    pathlib.Path.home() / "AppData" / "Roaming" / "Claude" / "settings.json",
    pathlib.Path.home() / "AppData" / "Local" / "Claude" / "settings.json",
]


def find_or_create_settings() -> pathlib.Path:
    # Return the first settings file that already exists
    for p in SETTINGS_CANDIDATES:
        if p.exists():
            return p
    # Nothing found -- create in the canonical ~/.claude location
    default = SETTINGS_CANDIDATES[0]
    default.parent.mkdir(parents=True, exist_ok=True)
    default.write_text("{}\n", encoding="utf-8")
    return default


def main():
    settings_path = find_or_create_settings()

    try:
        settings: dict = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"WARNING: {settings_path} is not valid JSON -- creating a fresh one.")
        settings = {}

    settings.setdefault("env", {})["CONTENT_CREATION_PLUGIN_ROOT"] = str(PLUGIN_ROOT)

    settings_path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    print(f"  Plugin root : {PLUGIN_ROOT}")
    print(f"  Settings    : {settings_path}")
    print()
    print("Done. Restart Claude Code for the env var to take effect.")

    # Credentials guidance
    workspace_creds = PLUGIN_ROOT / "secrets.env"
    home_creds = pathlib.Path.home() / ".claude" / "secrets.env"
    print()
    print("-" * 61)
    print("Credentials setup")
    print("-" * 61)
    if workspace_creds.exists():
        print(f"Credentials file found at {workspace_creds} (found)")
        print("All TI-connected skills will use it automatically.")
    elif home_creds.exists():
        print(f"Credentials file found at {home_creds} (found)")
        print("(Note: this file does not persist in container environments.)")
        print("For Cowork or any container environment, add secrets.env to")
        print("your workspace root instead.")
    else:
        print("Add a secrets.env file to your workspace root:")
        print()
        print(f"  {PLUGIN_ROOT / 'secrets.env'}")
        print()
        print("  TI_BASE_URL=https://academy.celonis.com")
        print("  TI_API_KEY=<your api key>")
        print("  TI_LEARNER_EMAIL=claude.uploader@celonis.com")
        print("  TI_LEARNER_PASSWORD=<password>")
        print()
        print("  # Optional: auto-update check (GitHub private repo hosting plugin releases)")
        print("  PLUGIN_UPDATE_GITHUB_REPO=<owner/repo>")
        print("  PLUGIN_UPDATE_GITHUB_TOKEN=<fine-grained-pat-with-contents-read>")
        print()
        print("This works everywhere, including Cowork and container environments.")
        print()
        print("Optional: macOS/Windows users can instead create")
        print(f"  {home_creds}")
        print("to avoid copying the file per project -- but this will not")
        print("persist in container environments (e.g. Cowork).")
    print("-" * 61)


if __name__ == "__main__":
    main()
