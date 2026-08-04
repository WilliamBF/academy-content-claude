#!/usr/bin/env python3
"""
check_update.py - SessionStart hook: check GitHub Releases for a plugin update.

Reads PLUGIN_UPDATE_GITHUB_REPO and PLUGIN_UPDATE_GITHUB_TOKEN from secrets.env,
calls the GitHub API to get the latest release tag, compares to the local version,
and outputs a one-line prompt to Claude only if an update is available.
Exits silently on any error or missing config.
"""

import glob
import json
import os
import sys
import urllib.request
from pathlib import Path

# Locate plugin root: env var first, then Cowork auto-detect
_root_str = os.environ.get("CONTENT_CREATION_PLUGIN_ROOT", "").strip()
if not _root_str:
    _matches = sorted(glob.glob(
        "/sessions/*/mnt/.local-plugins/marketplaces"
        "/local-desktop-app-uploads/content-creation-plugin"
    ))
    if _matches:
        _root_str = _matches[-1]

if not _root_str:
    sys.exit(0)

PLUGIN_ROOT = Path(_root_str).resolve()
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
        writable = True
        try:
            test = PLUGIN_ROOT / ".write_test"
            test.touch()
            test.unlink()
        except OSError:
            writable = False

        if writable:
            print(
                f"[PLUGIN UPDATE CHECK] A new version of the content-creation-plugin is available: "
                f"v{remote_tag} (installed: v{local_version}). "
                f"Tell the user and ask if they want to update. If yes, run /update-plugin."
            )
        else:
            print(
                f"[PLUGIN UPDATE CHECK] A new version of the content-creation-plugin is available: "
                f"v{remote_tag} (installed: v{local_version}). "
                f"Tell the user, but note the plugin directory is read-only here (Cowork sandbox) "
                f"so the update must be installed from Claude Code desktop app."
            )

except Exception:
    sys.exit(0)
