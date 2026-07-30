---
name: "update-plugin"
description: "Check GitHub Releases for a newer version of the content-creation-plugin and install it if available."
---

# Update Plugin

Check the configured GitHub repository for a newer version of the plugin and install it if one is found. Uses the GitHub Releases API — no MCP connector required, just a token in `secrets.env`.

---

## Step 0 -- Check the environment

```bash
echo "${CLAUDE_PLUGIN_ROOT:-NOT_SET}"
```

If `NOT_SET`: the plugin is not loaded. Tell the user and stop.

---

## Step 1 -- Read the installed version and GitHub config

```bash
python -c "
import json, os, sys
from pathlib import Path
root = Path(os.environ['CLAUDE_PLUGIN_ROOT'])
sys.path.insert(0, str(root))
from lib.config import _load_env_file
_load_env_file()
v = json.loads((root / '.claude-plugin/plugin.json').read_text())['version']
repo  = os.environ.get('PLUGIN_UPDATE_GITHUB_REPO',  '').strip()
token = os.environ.get('PLUGIN_UPDATE_GITHUB_TOKEN', '').strip()
print('version:', v)
print('repo:', repo or 'NOT_CONFIGURED')
print('token:', 'SET' if token else 'NOT_CONFIGURED')
"
```

If `repo` or `token` is `NOT_CONFIGURED`:
> Add the following to `secrets.env` in your workspace root (or `~/.claude/secrets.env`):
> ```
> PLUGIN_UPDATE_GITHUB_REPO=<owner/repo>
> PLUGIN_UPDATE_GITHUB_TOKEN=<your-github-token>
> ```
> Then retry.

---

## Step 2 -- Fetch the latest release from GitHub

```bash
python -c "
import json, os, sys, urllib.request
from pathlib import Path
root = Path(os.environ['CLAUDE_PLUGIN_ROOT'])
sys.path.insert(0, str(root))
from lib.config import _load_env_file
_load_env_file()
repo  = os.environ.get('PLUGIN_UPDATE_GITHUB_REPO', '').strip()
token = os.environ.get('PLUGIN_UPDATE_GITHUB_TOKEN', '').strip()
req = urllib.request.Request(
    f'https://api.github.com/repos/{repo}/releases/latest',
    headers={
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'content-creation-plugin',
    },
)
with urllib.request.urlopen(req, timeout=15) as r:
    release = json.loads(r.read())
tag = release.get('tag_name', '')
print('remote_tag:', tag)
for a in release.get('assets', []):
    if a['name'].endswith('.zip'):
        print('asset_id:', a['id'])
        print('asset_name:', a['name'])
        break
"
```

If the command fails with an HTTP error, check that `PLUGIN_UPDATE_GITHUB_TOKEN` is valid and has `Contents: Read` access to the repository.

---

## Step 3 -- Compare versions

Parse the `remote_tag` from Step 2 (strip leading `v`) and compare to the installed version from Step 1. Compare as version tuples so that `2.10.0 > 2.9.0`.

- If remote version <= installed version: tell the user they are already up to date, and stop.
- If remote version > installed version: proceed to Step 4.

---

## Step 4 -- Confirm with the user

Tell the user:
> A new version is available: **v{remote_version}** (installed: v{local_version}).
> Download and install? This will overwrite the plugin files and you will need to
> reload plugins afterwards (`/reload-plugins` or restart Claude Code).

Wait for confirmation before proceeding.

---

## Step 5 -- Download the zip

Replace `ASSET_ID_FROM_STEP_2` with the asset ID printed in Step 2.

```bash
python -c "
import os, sys, tempfile, urllib.request
from pathlib import Path
root = Path(os.environ['CLAUDE_PLUGIN_ROOT'])
sys.path.insert(0, str(root))
from lib.config import _load_env_file
_load_env_file()
repo  = os.environ.get('PLUGIN_UPDATE_GITHUB_REPO', '').strip()
token = os.environ.get('PLUGIN_UPDATE_GITHUB_TOKEN', '').strip()
asset_id = ASSET_ID_FROM_STEP_2
req = urllib.request.Request(
    f'https://api.github.com/repos/{repo}/releases/assets/{asset_id}',
    headers={
        'Authorization': f'token {token}',
        'Accept': 'application/octet-stream',
        'User-Agent': 'content-creation-plugin',
    },
)
dest = os.path.join(tempfile.gettempdir(), 'content-creation-plugin-update.zip')
with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
    f.write(r.read())
print('Downloaded to:', dest)
"
```

---

## Step 6 -- Extract and install

Replace `TEMP_ZIP_PATH` with the path printed in Step 5.

```bash
python -c "
import zipfile, os
from pathlib import Path

tmp_zip = 'TEMP_ZIP_PATH'
plugin_root = Path(os.environ['CLAUDE_PLUGIN_ROOT'])

with zipfile.ZipFile(tmp_zip) as z:
    members = z.namelist()
    # Detect a single top-level wrapper folder and strip it
    top_level = {m.split('/')[0] for m in members if m.split('/')[0]}
    prefix = (top_level.pop() + '/') if len(top_level) == 1 else ''

    for member in members:
        target_rel = member[len(prefix):] if prefix and member.startswith(prefix) else member
        if not target_rel or target_rel.endswith('/'):
            continue
        dest = plugin_root / target_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        with z.open(member) as src, open(dest, 'wb') as dst:
            dst.write(src.read())

os.remove(tmp_zip)
print('Installed to:', str(plugin_root))
"
```

---

## Step 7 -- Confirm and instruct reload

Tell the user:
> Plugin updated to **v{remote_version}**. To activate the new version:
> 1. Run `/reload-plugins` in this session, or
> 2. Start a new Claude Code session.

---

## One-time setup

### For users receiving the plugin

Add two lines to `secrets.env` in your workspace root (or `~/.claude/secrets.env` for a global setup):
```
PLUGIN_UPDATE_GITHUB_REPO=<owner/repo>
PLUGIN_UPDATE_GITHUB_TOKEN=<token-provided-by-the-maintainer>
```

The token needs only `Contents: Read` on the plugin repository. The session-start hook will silently check for updates automatically, or run `/update-plugin` at any time to check manually.

### For the maintainer publishing updates

1. Keep the plugin source as-is in the repository (`atlas-academy/` folder).
2. When ready to release a new version:
   a. Bump `version` in `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`
   b. Build the zip: run the build script from the repo root
   c. In GitHub: create a new Release, tag it `v{X.Y.Z}` (e.g. `v2.10.0`)
   d. Attach the zip (`content-creation-plugin-v{X.Y.Z}.zip`) as a release asset
3. Create a **fine-grained PAT** for distribution:
   - GitHub `Settings > Developer settings > Fine-grained personal access tokens`
   - Repository access: this repo only
   - Permissions: `Contents: Read`
   - Share this single token with all users — it's read-only and scoped to one repo
