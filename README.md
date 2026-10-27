# Content Creation Plugin (v2.34.1)

A course-authoring toolkit for planning, drafting, reviewing, and publishing training content to an LMS via its REST API. Organized as **Actions** (single operations) and **Routines** (multi-step sequences).

## Credentials

Scripts resolve credentials from a `secrets.env` file, checked in this order (first match wins):

1. `secrets.env` in the current working directory
2. `secrets.env` in a parent directory (walking up)
3. `secrets.env` at the plugin install folder
4. `~/.claude/secrets.env` (desktop only)
5. Pre-existing environment variables (e.g. a Claude Code `settings.json` `env` block)

| Variable | Purpose |
|---|---|
| `TI_BASE_URL` | LMS instance base URL |
| `TI_API_KEY` | API bearer token |
| `TI_LEARNER_EMAIL` | Learner account email — only needed for the `image_uploader.py` script fallback (see below) |
| `TI_LEARNER_PASSWORD` | Learner account password — same, script fallback only |
| `TI_UPLOAD_URL` | Browser upload page URL — same, script fallback only (currently unused even there) |

The last three exist only for the Python-script fallback path to image uploads. The **preferred** path — Playwright MCP — needs no stored credentials at all: the user logs in manually, in their own browser session, with their own account. See "Playwright MCP setup" below.

See `requirements.txt` for Python dependencies (`requests`, `beautifulsoup4`, `markdownify`; `playwright` optional for the image-upload script fallback, `python-docx`/`Pillow` optional for `migrate-rise-export`'s `--format docx` output). The preferred Playwright MCP image-upload path needs no Python dependency at all — just Node.js.

## Playwright MCP setup (image uploads)

`convert-course-to-html` and `migrate-rise-export` upload images to the LMS CDN. The preferred way to do this is the Playwright MCP — Claude drives a real, visible browser in your own session, and you log in manually with your own account. See `reference/playwright-mcp-image-upload.md` for full setup (adding the MCP server to `.mcp.json`, the Windows-specific `cmd /c npx` wrapper, and the step-by-step upload recipe). If Node.js isn't installed, get it via your company's software portal (e.g. Company Portal / Self Service) rather than downloading it directly.

A Python-script fallback (`image_uploader.py`) still exists for when the MCP isn't set up.

## Skills

### Actions (single operations)
- **guide** — Workspace status check and routing to the right next skill
- **create-course-project** — Scaffold a new course project folder structure
- **fetch-celonis-docs** — Crawl a docs section into source material, or search the Celonis docs for a question or topic and answer with sources cited
- **extract-local-resources** — Extract content from local PPTX/PDF/DOCX files
- **browse-TI-catalog** — List existing LMS courses with slugs and UUIDs
- **get-TI-course-structure** — Fetch a course's section/lesson/topic tree with UUIDs
- **evaluate-course-for-persona** — Evaluate a course against a target audience/persona
- **evaluate-course-for-id** — Instructional design checklist review
- **evaluate-course-for-sme** — Two-phase subject-matter-expert accuracy review
- **accessibility-check** — Audit a live course page by page against WCAG 2.2 AA and walk through fixes
- **update-snippets** — Detect outdated/legacy snippet structures on a live course page and migrate them to current markup
- **review-course-draft** — Human review pass on a Markdown draft via Google Docs

### Routines (multi-step sequences)
- **design-course-content** — Plan and outline course content
- **write-course-script** — Draft a publish-ready script with widget markup
- **review-course** — Orchestrate persona, ID, and SME reviews in one pass
- **write-exam-questions** — Create and refine qualification exam questions
- **convert-course-to-html** — Convert a script draft into publish-ready HTML, including image upload
- **extract-TI-course** — Extract an existing course or learning path into structured Markdown
- **migrate-rise-export** — Migrate an Articulate Rise 360 zip export into a course, via the existing HTML-conversion and upload steps
- **upload-course-to-TI** — Create sections, lessons, and topics from a course payload
- **update-TI-content** — Targeted update of a specific topic, lesson, or section
- **update-TI-course-metadata** — Update catalog metadata (description, tags, ribbon, duration, level, etc.)

## Upload workflow

1. Run `design-course-content` → `write-course-script` to produce a script draft
2. Run `convert-course-to-html` to generate HTML and upload images
3. Run `upload-course-to-TI` to push content (sections → lessons → topics)
4. Use `update-TI-content` / `update-TI-course-metadata` for targeted follow-up edits

## License

MIT
