# Architecture

BindingSolution is a small FastAPI app with a vanilla-JS single-page frontend.
It's a single-user, localhost-first tool, so it favours transparency (a
human-readable JSON store, no build step) over scale.

```
┌────────────────────────────────────────────────────────────┐
│ Browser SPA  (app/static: index.html · styles.css · app.js) │
│   Library · Connections · Strategies · Specs                │
└───────────────┬────────────────────────────────────────────┘
                │  fetch /api/*   +   poll /api/jobs/{id}
┌───────────────▼────────────────────────────────────────────┐
│ FastAPI  (app/server.py)                                    │
│   ├─ jobs.py      in-process background jobs + progress      │
│   ├─ analysis.py  Claude calls (structured outputs)         │
│   │    └─ mock.py  deterministic offline fallback           │
│   ├─ zotero_client.py   pyzotero (Web API / local Zotero 7) │
│   ├─ demo_data.py       bundled sample library              │
│   ├─ specs.py     PDF/Word/MD/text extraction               │
│   └─ store.py     thread-safe JSON persistence (data/)      │
└─────────────────────────────────────────────────────────────┘
```

## How AI analysis works

`app/analysis.py` wraps the Anthropic Python SDK. Every analysis uses
**structured outputs** so the model is constrained to a known schema and we get
a validated object back:

```python
response = client.messages.parse(
    model="claude-opus-4-8",
    max_tokens=...,
    system=_SYSTEM,
    messages=[{"role": "user", "content": prompt}],
    output_format=ProjectCategory,   # a Pydantic model from app/schemas.py
    thinking={"type": "adaptive"},   # on cross-project reasoning + planning
)
result = response.parsed_output       # a validated ProjectCategory
```

The Pydantic models in `app/schemas.py` are the single source of truth: they
generate the JSON schema sent to the API **and** define the contract the
frontend renders. Refusals (`stop_reason == "refusal"`) and truncation
(`max_tokens`) are turned into clear errors surfaced in the UI.

Cross-project work (connections, reading strategies) uses adaptive thinking and
a larger token budget; high-volume per-paper summarization keeps outputs tight.

**Offline mode:** if no `ANTHROPIC_API_KEY` is set (or `MOCK_LLM=true`),
`app/mock.py` produces deterministic results in the same shape, derived from
the real input (tags, titles). The whole app — and the test suite — runs with
no key and no network.

## Background jobs

Analyses and syncs can take a while, so write endpoints return a `job_id`
immediately (`app/jobs.py` runs the work in a daemon thread) and the frontend
polls `GET /api/jobs/{id}` for live progress. Spec screening persists relevant
hits incrementally, so partial progress survives an interruption.

### Project specs (paper suggestions)

The **Project specs** view is a two-tab SPA panel (`Upload & manage` ·
`Suggested papers`):

1. **Upload** — `POST /api/specs` extracts text (PDF/Word/MD/txt), validates
   that the content is a real project brief (`SpecValidation`), and stores it.
2. **Screen** — `POST /api/specs/{id}/analyze` assesses each paper in the
   active library but only persists **core** and **supporting** hits in
   `spec.analysis`. The UI lists those in the **Suggested papers** tab with
   `relevance_explanation` and optional `use_for` tags.

## Persistence

`app/store.py` is a thread-safe wrapper over one JSON file
(`data/library.json`, gitignored). Writes are atomic (temp-file + replace) and
a corrupt file is set aside rather than crashing. No database to run.

## API reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/status` | Config + library summary |
| `POST` | `/api/library/sync` | Sync Zotero (`{"source":"zotero"}`) or load demo (`{"source":"demo"}`) → job |
| `DELETE` | `/api/library` | Purge all local data (projects, analyses, plans, specs) |
| `GET` | `/api/projects` | List projects (summaries) |
| `GET` | `/api/projects/{key}` | One project with its papers |
| `POST` | `/api/projects/{key}/categorize` | Categorize one project → job |
| `POST` | `/api/projects/categorize-all` | Categorize every project → job |
| `POST` | `/api/connections` | Find cross-project connections → job |
| `GET` | `/api/connections` | Latest connection map |
| `POST` | `/api/strategies` | Generate a reading plan (`mode`, `goal`, `project_keys`) → job |
| `GET` / `DELETE` | `/api/strategies[/{id}]` | List / delete saved plans |
| `POST` | `/api/specs` | Upload a spec (file or `text`) |
| `GET` / `DELETE` | `/api/specs[/{id}]` | List / fetch / delete specs |
| `POST` | `/api/specs/{id}/analyze` | Screen library; store only relevant papers → job |
| `GET` | `/api/jobs/{id}` | Poll a background job |

Endpoints that return `{"job_id": ...}` are asynchronous — poll `/api/jobs/{id}`
until `status` is `done` (then read `result`) or `error`.

## Tests

`tests/test_api.py` drives the full API through FastAPI's `TestClient` in
offline mode (`MOCK_LLM=true`), including self-contained PDF/Word spec uploads.
Run with `make test`.

## Project layout

```
app/
  server.py        FastAPI routes + static hosting
  __main__.py      `python -m app` entry point (uvicorn)
  config.py        .env-driven settings
  store.py         JSON persistence
  jobs.py          background job runner
  analysis.py      Claude analysis (structured outputs)
  schemas.py       Pydantic output schemas
  mock.py          offline/deterministic analysis
  zotero_client.py Zotero ingest (optional pyzotero)
  demo_data.py     bundled sample library
  specs.py         spec text extraction
  static/          the single-page UI
scripts/           setup.sh, run.sh
tests/             API tests (offline)
docs/              this documentation
```
