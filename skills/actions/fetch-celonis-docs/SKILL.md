---
name: "fetch-celonis-docs"
description: "Get Celonis product documentation from docs.celonis.com, which sits behind SSO and can't be fetched with a normal web request. Two jobs: (1) crawl a docs section by URL into a course's 01_Source_Material folder, or (2) look up the pages that answer a question or cover a topic (or fetch exact docs URLs the user pastes) and answer from them with sources cited. Trigger when the user asks to crawl/fetch/pull Celonis docs, asks to look something up in the Celonis docs, or pastes a docs.celonis.com link. Also, briefly and without fetching anything: when a question about a Celonis product feature can't be answered confidently from local material (the course's source files, the workspace, the conversation), add ONE line offering to check docs.celonis.com and wait for a yes. Do not offer when the answer is clear locally or the question isn't about Celonis products, and never ask for the session cookie before the user accepts. Do NOT use for general course writing or review tasks unless a specific Celonis claim is uncertain."
---

# Celonis Docs — Crawl or Search

docs.celonis.com requires SSO login, so Claude can't read it with a normal web request. This skill uses the user's own `sf_session` cookie (or a one-time browser login) to reach it. It has two jobs:

| Job | Use when | Script |
|---|---|---|
| **A. Crawl a section** | The user wants a whole docs section saved as course source material | `crawl_celonis_docs.py` |
| **B. Search and answer** | The user asks a question, wants a topic summarised, or gives exact docs URLs | `search_docs.py` |

The user never types script flags: they say what they want in plain language and Claude chooses the job and runs the script.

---

# Job A — Crawl a section into course source material

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
printf '<ENTRY_URL>\n<OUTPUT_PATH>\n' | python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/fetch-celonis-docs/crawl_celonis_docs.py"
```

---

### Mode B — Playwright mode (macOS / Windows, one-time browser login)

Requires Playwright + Chromium. On first run a browser window opens for SSO login; the session is saved to `~/.claude/celonis_docs_session.json` and reused automatically.

```bash
pip install beautifulsoup4 markdownify playwright --break-system-packages -q
python -m playwright install chromium --quiet
printf '<ENTRY_URL>\n<OUTPUT_PATH>\n' | python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/fetch-celonis-docs/crawl_celonis_docs.py"
```

When the browser opens: click **Celonaut Login**, complete the SSO flow, then press **Enter** in the terminal.

---

The script auto-detects which mode to use: if `CELONIS_DOCS_SESSION_COOKIE` is set in `secrets.env`, cookie mode is used; otherwise it falls back to Playwright. If neither is available it prints clear setup instructions and exits.

---

## Step 4 — Report results (crawl)

Tell the user:
- How many `.md` files were saved
- Where they were saved (user-facing path)
- List file names (first 10 if many)
- Note any `[ERROR]` lines
- Remind them these files are ready as source material for course drafting

---

# Job B — Search and answer from the docs

## When to offer it (without being asked)

If the user asks about a Celonis product feature and the answer is not clear from local material, add one line at the end of your reply and stop there, for example: *"I'm not certain about this. I can check docs.celonis.com if you'd like (I'd need your session cookie)."* Then wait.
- Do not fetch, and do not ask for the cookie, until the user says yes.
- Say nothing if the answer is clear locally, or the question isn't about Celonis products.
- During course writing or review, offer only for a specific claim you are unsure of, not for every Celonis term.

## Step 1 — Get the session cookie

Check whether `CELONIS_DOCS_SESSION_COOKIE` is already set in `secrets.env` (the same setting Job A uses). If it is, the script finds it itself. If not, ask the user for the value:
1. Open docs.celonis.com in a browser and log in.
2. DevTools (F12) → Application (Chrome) or Storage (Firefox) → Cookies → `docs.celonis.com`.
3. Copy the **Value** of the cookie named `sf_session`.

Pass a pasted value with `--cookie <value>`: it is used for that run only and never written to a file. To keep it for later sessions the user adds `CELONIS_DOCS_SESSION_COOKIE=sf_session=<value>` to `secrets.env`. The cookie expires after some hours; a "redirected off the docs domain" warning or a sitemap error means it expired, so ask for a fresh one and retry.

On desktop with a saved Playwright login (Job A, Mode B) the script can use that session's cookie automatically. This does not work in Cowork.

## Step 2 — Choose the mode and run it

Use a scratch folder for `<output_dir>` (for example `./_docs_scratch`); these are working files for answering the question, not a deliverable. In Cowork this works in cookie mode (no browser), but keep the cookie in the plugin-folder `secrets.env` or pass `--cookie`, because `~/.claude` does not persist there.

```bash
pip install beautifulsoup4 markdownify requests --break-system-packages -q
python "$CONTENT_CREATION_PLUGIN_ROOT/skills/actions/fetch-celonis-docs/search_docs.py" <output_dir> <mode> [--cookie <value>]
```

| The user… | Mode | Notes |
|---|---|---|
| pastes docs.celonis.com link(s) | `--url <url> [<url> ...]` | Fetch exactly those pages. Fastest, and avoids a search picking the wrong page. |
| names a topic: "summarise X", "how many pages cover X", "overview of X" | `--topic <keywords> --fetch` | Only mode with complete coverage. Drop `--fetch` for a list or count without downloading. |
| asks a narrow, specific question | `<keywords> [--top N]` | Fetches the best N slug matches (default 5). |
| wants one known section's pages | `--section <entry_url> [--fetch]` | Rarely needed; `--topic` uses it internally. |

Why `--topic` is the default for coverage: keyword matching alone misses sibling pages whose URL doesn't mention the topic (a page titled "FAQ" under the Context Model section has the slug `ccm-faq.html`), and the section sidebar alone misses pages about the topic that live elsewhere on the site. `--topic` runs both and deduplicates.

If nothing matches, rephrase using Celonis's own product terminology before telling the user nothing was found.

## Step 3 — Read, answer, cite

1. For a full-coverage request, read every fetched file, not a sample. For a narrow question, read the matched pages fully; titles alone mislead (for example "Views" is both a product area and a generic word).
2. Answer from what the docs actually say.
3. Cite each page used (title and source URL from the file header). For a summary across many pages, list all the source pages.
4. If no page answers the question, say so plainly instead of filling the gap, and ask for different search terms.

Give the answer with its sources, not a narrated account of what was searched.
