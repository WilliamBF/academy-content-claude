# Content Creation Plugin (v1.2.0)

Celonis Academy content creation toolkit for authoring, transforming, and publishing courses to the Thought Industries LMS.

## Setup

Run the appropriate setup script for your OS:

- **Mac/Linux:** `bash setup-prefilled.sh`
- **Windows:** `powershell -ExecutionPolicy Bypass -File setup-prefilled.ps1`

The setup scripts:
1. Install Python 3.12 (if missing)
2. Install required Python libraries (requests, beautifulsoup4, python-dotenv, markdownify)
3. Set persistent environment variables (`TI_BASE_URL`, `TI_API_KEY`, etc.)
4. Write config files for both plugins

## Credentials

This plugin reads credentials from **environment variables** (set by the setup scripts):

| Variable | Purpose |
|---|---|
| `TI_BASE_URL` | TI instance URL |
| `TI_API_KEY` | API bearer token |
| `TI_LEARNER_EMAIL` | Learner account email |
| `TI_LEARNER_PASSWORD` | Learner account password |
| `TI_UPLOAD_URL` | Browser upload page URL |
| `TI_ANALYTICS_DISABLED` | Set to `1` to disable TI analytics |

## Skills

### Actions (single operations)
- **new-course-project** — Scaffold a new course folder
- **crawl-celonis-docs** — Crawl Celonis docs into .md reference files

### Routines (multi-step sequences)
- **course-to-html** — Google Doc → .md draft → TI-ready HTML
- **lms-upload** — Upload HTML to TI LMS (iterative API pattern)
- **lms-extract** — Pull existing course from TI into .md files
- **academy-course-scripting** — Draft and refine course scripts

## Upload workflow

1. Run `course-to-html` to generate HTML from Google Doc
2. Run `image_uploader.py` to upload images to TI CDN
3. Run `patch_cdn_urls.py` to replace `PENDING_CDN_UPLOAD` placeholders
4. Run `lms-upload` to push content to TI (iterative: sections → lessons → topics)

**Important:** Never run `lms-upload` while HTML still contains `PENDING_CDN_UPLOAD` placeholders.

## Requirements

See `requirements.txt` for Python dependencies. The setup scripts install these automatically.

## License

MIT
