"""
Credentials for content-creation-plugin.

Resolution order (first match wins):
  1. secrets.env in the workspace root or any parent folder (up to 5 levels)
  2. {plugin_root}/secrets.env -- place once at install location, works in Cowork
  3. ~/.claude/secrets.env -- desktop/macOS only (home dir is ephemeral in Cowork)
  4. Existing environment variables (e.g. set in Claude Code settings.json)

No config.json caching -- stateless on every call.
"""

import glob
import os
import sys
from pathlib import Path


def find_plugin_root() -> "Path | None":
    """
    Locate the content-creation-plugin root directory.

    Checks CONTENT_CREATION_PLUGIN_ROOT env var first, then falls back to
    the Cowork Linux session mount path when the env var is not set.
    Returns a Path object or None if not found.
    """
    root = os.environ.get("CONTENT_CREATION_PLUGIN_ROOT", "").strip()
    if root and Path(root).is_dir():
        return Path(root)

    # Cowork mounts the plugin read-only at a predictable Linux path
    matches = sorted(glob.glob(
        "/sessions/*/mnt/.local-plugins/marketplaces"
        "/local-desktop-app-uploads/content-creation-plugin"
    ))
    if matches:
        return Path(matches[-1])

    return None


def _load_env_file(override: bool = False):
    """
    Look for secrets.env by walking up from CWD, then checking ~/.claude/secrets.env.
    Loads KEY=VALUE lines into os.environ.

    When override=True, values from the file overwrite existing env vars.
    When override=False (default), existing env vars take priority.

    Returns True if any file was found and loaded.
    """
    candidates = [
        os.path.join(os.getcwd(), "secrets.env"),
        os.path.join(os.getcwd(), ".env"),
    ]

    # Also check parent dirs (useful when scripts run from subfolders)
    cwd = os.getcwd()
    for _ in range(5):
        parent = os.path.dirname(cwd)
        if parent == cwd:
            break
        candidates.append(os.path.join(parent, "secrets.env"))
        candidates.append(os.path.join(parent, ".env"))
        cwd = parent

    # Plugin install folder: persists in Cowork (mounted from Windows), works on desktop.
    # setup.py already points users here — this closes the gap so scripts actually find it.
    try:
        plugin_root = find_plugin_root()
        if plugin_root:
            candidates.append(str(plugin_root / "secrets.env"))
    except Exception:
        pass

    # Central user-level fallback (desktop only — ephemeral home in Cowork)
    candidates.append(os.path.join(os.path.expanduser("~"), ".claude", "secrets.env"))

    for filepath in candidates:
        if os.path.exists(filepath):
            loaded = False
            with open(filepath, "r", encoding="utf-8-sig") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if override or not os.environ.get(key):
                            os.environ[key] = value
                            loaded = True
            if loaded:
                return True
    return False


def resolve_credentials() -> dict:
    """
    Read TI credentials from secrets.env (always loaded first, takes priority
    over any pre-existing environment variables so that the project-local file
    is always authoritative).

    Returns dict with keys:
        base_url, api_key, learner_email, learner_password, upload_url
    """
    # Always load from file with override so secrets.env wins over stale env vars
    _load_env_file(override=True)

    base_url = os.environ.get("TI_BASE_URL", "").strip().rstrip("/")
    api_key = os.environ.get("TI_API_KEY", "").strip()

    if not base_url:
        print("[ERROR] TI_BASE_URL not found. Set credentials using one of:", file=sys.stderr)
        print("  - secrets.env in the plugin install folder (works in Cowork — run python setup.py)", file=sys.stderr)
        print("  - secrets.env in your workspace root (workspace-specific, always found)", file=sys.stderr)
        print("  - ~/.claude/secrets.env (desktop / macOS only — ephemeral in Cowork)", file=sys.stderr)
        print("  - TI_BASE_URL in Claude Code settings.json -> \"env\" block (no file needed)", file=sys.stderr)
        sys.exit(1)

    if not api_key:
        print("[ERROR] TI_API_KEY not found. Set credentials using one of:", file=sys.stderr)
        print("  - secrets.env in the plugin install folder (works in Cowork — run python setup.py)", file=sys.stderr)
        print("  - secrets.env in your workspace root (workspace-specific, always found)", file=sys.stderr)
        print("  - ~/.claude/secrets.env (desktop / macOS only — ephemeral in Cowork)", file=sys.stderr)
        print("  - TI_API_KEY in Claude Code settings.json -> \"env\" block (no file needed)", file=sys.stderr)
        sys.exit(1)

    return {
        "base_url": base_url,
        "api_key": api_key,
        "learner_email": os.environ.get("TI_LEARNER_EMAIL", "").strip(),
        "learner_password": os.environ.get("TI_LEARNER_PASSWORD", "").strip(),
        "upload_url": os.environ.get("TI_UPLOAD_URL", "").strip(),
    }
