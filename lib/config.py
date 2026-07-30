"""
Credentials for content-creation-plugin.

Resolution order (first match wins):
  1. secrets.env in the workspace root or any parent folder (up to 5 levels)
  2. ~/.claude/secrets.env -- one-time central setup (create once, works from any workspace)
  3. Existing environment variables (e.g. set in Claude Code settings.json)

No config.json caching -- stateless on every call.
"""

import os
import sys


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

    # Central one-time setup location -- checked last so workspace files take priority
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
        print("[ERROR] TI_BASE_URL not found.", file=sys.stderr)
        print("        Add a secrets.env file to your workspace root (standard, works everywhere).", file=sys.stderr)
        print("        Or create ~/.claude/secrets.env for persistent non-container setups (macOS/Windows).", file=sys.stderr)
        sys.exit(1)

    if not api_key:
        print("[ERROR] TI_API_KEY not found.", file=sys.stderr)
        print("        Add a secrets.env file to your workspace root (standard, works everywhere).", file=sys.stderr)
        print("        Or create ~/.claude/secrets.env for persistent non-container setups (macOS/Windows).", file=sys.stderr)
        sys.exit(1)

    return {
        "base_url": base_url,
        "api_key": api_key,
        "learner_email": os.environ.get("TI_LEARNER_EMAIL", "").strip(),
        "learner_password": os.environ.get("TI_LEARNER_PASSWORD", "").strip(),
        "upload_url": os.environ.get("TI_UPLOAD_URL", "").strip(),
    }
