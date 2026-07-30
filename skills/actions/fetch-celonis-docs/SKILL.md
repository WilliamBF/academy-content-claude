---
name: "fetch-celonis-docs"
description: "Crawl a Celonis docs section by URL, follow its sidebar navigation, and save pages as .md files into a course's 01_Source_Material folder."
---

# Crawl Celonis Docs — Fetch Reference Material

Fetch Celonis product documentation as .md source material for a course project. Runs the co-located `crawl_celonis_docs.py` script.

---

## Step 1 — Gather inputs

Ask the user for:

1. **The docs URL to crawl** — a full URL or a topic area (e.g. "Studio", "Data Integration"). Common entry points:
   - Studio: `https://docs.celonis.com/en/studio.html`
   - Data Integration: `https://docs.celonis.com/en/data-integration.html`
   - Process Mining: `https://docs.celonis.com/en/process-mining.html`
   - Views: `https://docs.celonis.com/en/views.html`
   - Action Flows: `https://docs.celonis.com/en/action-flows.html`
   - ML Workbench: `https://docs.celonis.com/en/ml-workbench.html`

2. **Which course project to save into** — list existing course folders under `courses/` so the user can pick one.

---

## Step 2 — Set the output path

- Course project: `courses/<course-name>/01_Source_Material/docs/`
- General reference: `_guidelines/celonis-docs/<topic-slug>/`

Create the folder if it doesn't exist.

---

## Step 3 — Authenticate and run the crawler

The crawler supports two modes. Check which applies and set up accordingly before running.

---

### Mode A — Cookie mode (recommended; works everywhere including Cowork)

No browser or Playwright installation needed. Requires a one-time cookie copy from your browser.

**How to get the `sf_session` cookie (Chrome):**
1. Open [docs.celonis.com](https://docs.celonis.com) in Chrome and make sure you are logged in.
2. Press **F12** to open DevTools.
3. Go to the **Application** tab → expand **Cookies** in the left panel → click **https://docs.celonis.com**.
4. Find the cookie named **`sf_session`** in the table.
5. Click on it and copy the full **Value** field.
6. Add to your `secrets.env`:
   ```
   CELONIS_DOCS_SESSION_COOKIE=sf_session=<paste value here>
   ```

**How to get the `sf_session` cookie (Firefox):**
1. Open [docs.celonis.com](https://docs.celonis.com) and log in.
2. Press **F12** → **Storage** tab → **Cookies** → **https://docs.celonis.com**.
3. Find `sf_session`, copy the **Value**.
4. Add to `secrets.env` as above.

The cookie is valid for the duration of your SSO session (typically hours to days). When it expires the script will print a clear error — just repeat the steps above to refresh it.

**Run (cookie mode — no extra install needed):**
```bash
pip install beautifulsoup4 markdownify requests --break-system-packages -q
printf '<ENTRY_URL>\n<OUTPUT_PATH>\n' | python "$CLAUDE_PLUGIN_ROOT/skills/actions/fetch-celonis-docs/crawl_celonis_docs.py"
```

---

### Mode B — Playwright mode (macOS / Windows, one-time browser login)

Requires Playwright + Chromium. On first run a browser window opens for SSO login; the session is saved to `~/.claude/celonis_docs_session.json` and reused automatically.

```bash
pip install beautifulsoup4 markdownify playwright --break-system-packages -q
python -m playwright install chromium --quiet
printf '<ENTRY_URL>\n<OUTPUT_PATH>\n' | python "$CLAUDE_PLUGIN_ROOT/skills/actions/fetch-celonis-docs/crawl_celonis_docs.py"
```

When the browser opens: click **Celonaut Login**, complete the SSO flow, then press **Enter** in the terminal.

---

The script auto-detects which mode to use: if `CELONIS_DOCS_SESSION_COOKIE` is set in `secrets.env`, cookie mode is used; otherwise it falls back to Playwright. If neither is available it prints clear setup instructions and exits.

---

## Step 4 — Report results

Tell the user:
- How many `.md` files were saved
- Where they were saved (user-facing path)
- List file names (first 10 if many)
- Note any `[ERROR]` lines
- Remind them these files are ready as source material for course drafting
