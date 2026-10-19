# Playwright MCP image upload (preferred path)

Full recipe for uploading images to the TI CDN by driving a real browser live, via the Playwright MCP, instead of running `image_uploader.py`. Used by `convert-course-to-html` and `migrate-rise-export`.

## What this is

The Playwright MCP (`@playwright/mcp`) gives Claude live browser-control tools running in the user's own session — a real browser window the user can see and sign into. This is different from `image_uploader.py`, which drives its own separate, headless Playwright install and needs `TI_LEARNER_EMAIL`/`TI_LEARNER_PASSWORD` stored in `secrets.env` to log in non-interactively.

With the MCP path, the user logs in manually, with their own personal Celonis account, in the browser window Claude opens. No credential for this step is ever typed in chat or written to a file.

## One-time setup

**Node.js is required** (`npx` needs it). Check with:
```bash
node --version
```
If it's missing, install Node.js via your company's software portal (e.g. Company Portal / Self Service) — check with IT if you're unsure which to use. Don't instruct users to download it directly from nodejs.org on a managed machine.

**Add the Playwright MCP server.** No `.mcp.json` exists in this repo by default — create or edit one at the project root:

```json
{
  "mcpServers": {
    "playwright": {
      "command": "cmd",
      "args": ["/c", "npx", "@playwright/mcp@latest"]
    }
  }
}
```

- **Windows** needs the `cmd /c` wrapper shown above — `npx` is a `.cmd` shim and won't launch directly. Confirmed working in the 2026-10-15 pilot.
- **macOS**: plain `"command": "npx", "args": ["@playwright/mcp@latest"]` is expected to work (no `cmd /c` wrapper needed there). **This is an unverified assumption** — the pilot was Windows-only. Confirm on a Mac machine before treating this as settled.
- Optional flags: `--user-data-dir <folder>` for a persistent login profile across sessions (avoids re-logging-in every time), `--viewport-size` to control the browser window size.
- Claude Code needs to reconnect (restart the session, or reload MCP servers) after editing `.mcp.json` before the new tools appear.

## How Claude decides which path to use

Check whether Playwright MCP browser tools (`browser_navigate`, `browser_run_code_unsafe`, `browser_file_upload`, etc.) are present in the current toolset.

This is different from the Mode A/B pattern used in `fetch-celonis-docs` (which auto-detects based on an env var a script can read). There's no script here to inspect anything — Claude itself decides, directly from its own available tools, which path to take.

- Tools present → follow the recipe below.
- Tools absent, or the user doesn't want to set up Node/`.mcp.json` right now → fall back to `image_uploader.py` (see "When to fall back" below).

## Step-by-step recipe

1. **Stage images.** Copy the images into the MCP's allowed uploads folder (its session uploads directory / `.playwright-mcp` subfolder) first — the MCP can't reach arbitrary host paths.

2. **Navigate to the dedicated upload course.** Use the exact same URL `image_uploader.py` uses — copy it from that script rather than retyping it, so the two never drift apart:
   ```
   https://academy.celonis.com/learn/manager/course/82c68700-2c31-4ddd-9595-911fdea1b982/sections?tab=content
   ```
   Never navigate to a different course without the user explicitly asking for it in that session.

3. **Log in.** If not already signed in, this redirects to `academy-login.celonis.com`. The user signs in manually, with their own personal account, in the browser window. Never ask for or type a password in chat; never write one to `secrets.env`.

   **Gotcha — learner vs. manager view:** the same account can have both a learner and a manager role, and after login the session may still be in learner mode from a previous state. If the page shows an info banner reading "You are currently a learner.", click the **Return to Management** button in it, then wait for the course manager page to load before continuing. Don't try to Add Page from the learner view — the manager controls aren't there.

   **Gotcha:** the redirect can land on an old, pre-existing page instead of a blank slate. Never type into whatever loads — always click **Add Page** → the **Text** page-type button to create a fresh page.

4. **Title the page.** Fill the "Page Title" textbox with a clear, dated title (e.g. `Image Upload 2026-10-16`).

5. **Batch-upload images.** Work in batches of about 10-15 images per `browser_run_code_unsafe` call. For each image in a batch:
   - Click `a.re-button[data-re-name='image']`.
   - Wait for `div.upload-redactor-box` to appear.
   - Upload with `page.locator("input[type='file']").first().setInputFiles(path)` as the **primary** method — not a fallback. **Never** use the file-chooser-event pattern (`expect_file_chooser`) in a loop; it stalled and swallowed return values during the pilot.
   - Wait for the new figure to appear, then move on.

   Example batch-upload pattern for one `browser_run_code_unsafe` call:
   ```javascript
   async function uploadBatch(page, items) {
     // items: [{ path: "/abs/path/in/uploads/dir/img1.png", filename: "img1.png" }, ...]
     const results = {};
     for (const { path, filename } of items) {
       const before = await page.locator("figure.redactor-uploaded-figure img").count();
       await page.locator("a.re-button[data-re-name='image']").click();
       await page.locator("div.upload-redactor-box").waitFor({ state: "visible", timeout: 5000 });
       await page.locator("input[type='file']").first().setInputFiles(path);
       await page.waitForFunction(
         (n) => document.querySelectorAll("figure.redactor-uploaded-figure img").length > n,
         before,
         { timeout: 30000 }
       );
       const imgs = await page.locator("figure.redactor-uploaded-figure img").all();
       const last = imgs[imgs.length - 1];
       const src = await last.getAttribute("src");
       results[filename] = src && src.endsWith("-" + filename) ? src : (src || null);
       await page.locator("figure.redactor-uploaded-figure").last().click();
       await page.keyboard.press("ArrowDown");
     }
     return results;
   }
   ```

6. **Match filenames to URLs.** The CDN prepends a random prefix to each filename, so match with `url.endsWith('-' + filename)` rather than exact equality.

7. **Write `cdn_map.json` incrementally.** Merge each batch's results into the map and write it to disk after every batch — not just at the end. This mirrors `image_uploader.py`'s own resume-by-skip contract: on a re-run, skip any filename already present with a truthy (non-null) value.

8. **Verify before saving.** Confirm every input filename has a mapped, non-null URL. Optionally spot-check one or two URLs with an HTTP request expecting 200. Report any unmapped files instead of silently proceeding to save.

9. **Save.** Two "Save" buttons exist in the DOM; click the first one. **Don't trust the "Last saved" label** as proof the save worked — it was empty in one pilot check despite a successful save. Verify by reopening the page or re-reading its state instead.

## Gotchas / recovery

- **Stuck file-chooser dialog** — if one gets queued and stalls everything, call `browser_file_upload` repeatedly with no paths to cancel it. Other tools refuse to run while a chooser is pending.
- **No `require` / Node `fs` inside `browser_run_code_unsafe`** — can't read local files that way. Use `setInputFiles`, which the MCP resolves against its own allowed folder. In-page `fetch()` of the CDN URL is also blocked — don't try to pull image bytes through page JS.
- **No bulk upload** — Redactor's file input is single-file only (`multiple: false`); dropping multiple files at once only uploaded one in testing. The per-image loop is the only route, and it's already cheap (~0.8s/image in the pilot).
- **Transient "classifier temporarily unavailable" error** — retry after a short wait.
- **Screenshots are viewport-only**, and a resize doesn't always persist — re-resize the window after login if consistent captures matter.

## When to fall back to the Python script

Use `image_uploader.py` instead when:
- Playwright MCP tools aren't present in Claude's current toolset, and the user doesn't want to set up Node.js / `.mcp.json` right now, or
- The MCP path hits unrecoverable errors after a reasonable number of retries.

The script needs `TI_LEARNER_EMAIL`/`TI_LEARNER_PASSWORD` set in `secrets.env` and a local Playwright install (`pip install playwright && playwright install chromium`) — see `convert-course-to-html/SKILL.md` for the exact invocation.
