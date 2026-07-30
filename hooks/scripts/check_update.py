#!/usr/bin/env python3
"""
check_update.py - SessionStart hook: check GitHub Releases for a plugin update.

Reads PLUGIN_UPDATE_GITHUB_REPO and PLUGIN_UPDATE_GITHUB_TOKEN from secrets.env,
calls the GitHub API to get the latest release tag, compares to the local version,
and outputs a one-line prompt to Claude only if an update is available.
Exits silently on any error or missing config.
"""

import json
import os
import sys
import urllib.request
from pathlib import Path

PLUGIN_ROOT = (
    Path(os.environ.get("CLAUDE_PLUGIN_ROOT", "")).resolve()
    if os.environ.get("CLAUDE_PLUGIN_ROOT")
    else None
)

if not PLUGIN_ROOT:
    sys.exit(0)

sys.path.insert(0, str(PLUGIN_ROOT))

try:
    from lib.config import _load_env_file
    _load_env_file()
except Exception:
    pass

try:
    repo  = os.environ.get("PLUGIN_UPDATE_GITHUB_REPO",  "").strip()
    token = os.environ.get("PLUGIN_UPDATE_GITHUB_TOKEN", "").strip()
    if not repo or not token:
        sys.exit(0)

    plugin_json_path = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
    local_version = json.loads(
        plugin_json_path.read_text(encoding="utf-8")
    ).get("version", "unknown")

    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "content-creation-plugin",
        },
    )
    with urllib.request.urlopen(req, timeout=8) as resp:
        release = json.loads(resp.read())

    remote_tag = release.get("tag_name", "").lstrip("v")
    if not remote_tag:
        sys.exit(0)

    def to_tuple(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except Exception:
            return (0,)

    if to_tuple(remote_tag) > to_tuple(local_version):
        print(
            f"[PLUGIN UPDATE CHECK] A new version of the content-creation-plugin is available: "
            f"v{remote_tag} (installed: v{local_version}). "
            f"Tell the user and ask if they want to update. "
            f"If yes, run /update-plugin."
        )

except Exception:
    sys.exit(0)
