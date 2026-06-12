# Architecture

BindingSolution is a small FastAPI app with a vanilla-JS single-page frontend.
It's a single-user, localhost-first tool, so it favours transparency (a
human-readable JSON store, no build step) over scale.

```
┌────────────────────────────────────────────────────────────┐
│ Browser SPA  (app/static: index.html · styles.css · app.js) │
│   Library · Connections · Groups · Strategies · Specs       │
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
│   ├─ spec_strategy.py spec → filtered projects + plan map   │
│   ├─ reading_schedule.py  per-paper time + day schedule     │
│   └─ store.py     thread-safe JSON persistence (data/)      │
└─────────────────────────────────────────────────────────────┘
```

## Frontend layout

The SPA (`app/static/`) is a hash router with five views. CSS centers the whole
shell (`max-width: 1680px`, `margin: 0 auto`) so the green sidebar and main pane
move together on ultrawide monitors. The sidebar (`--rail-w: 288px`) holds
navigation and status chips; **Sync library** / **Purge library** and per-view
actions sit in the hero toolbar. Main content fills the remaining width without
a separate max-width offset (no sidebar/content gap on large displays).

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

**Billing note:** live mode bills your Anthropic key per API call. Spec
screening issues one call per paper in the active library; other features use
one call per job or per project. See [BILLING.md](BILLING.md).

## Background jobs

Analyses and syncs can take a while, so write endpoints return a `job_id`
immediately (`app/jobs.py` runs the work in a daemon thread) and the frontend
polls `GET /api/jobs/{id}` for live progress. `GET /api/jobs` lists in-flight
and recent jobs (optional `?active=true`). The sidebar **Running** panel tracks
active job ids in `sessionStorage` so a refresh reconnects to server threads
still in the registry.

Closing a progress modal, navigating between views, or reloading the page does
**not** cancel a job — only stopping the Python process (e.g. Ctrl+C in the
terminal running `make run`) does. Dismissing a row in **Running** hides it from
the UI only. Spec screening persists relevant hits incrementally, so partial
progress survives an interruption.

### Spec (library screen + PubMed discovery)

The **Spec** view is a two-tab SPA panel (`Upload & manage` · `Suggested papers`):

1. **Upload** — `POST /api/specs` extracts text (PDF/Word/MD/txt), validates
   that the content is a real project brief (`SpecValidation`), and stores it.
2. **Screen library** — `POST /api/specs/{id}/analyze` assesses each paper in the
   active library but only persists **core** and **supporting** hits in
   `spec.analysis`. The UI lists those under **Library matches** on the upload tab.
3. **Discover on PubMed** — `POST /api/specs/{id}/discover` (`app/discovery.py`)
   builds a query from spec text and categorized keywords, fetches candidates via
   NCBI eutils, excludes titles already in the library, scores each hit by keyword
   overlap (title/abstract), and keeps **up to five** rows at or above
   `MIN_RELEVANCE_SCORE` (55). A relative drop-off rule trims weak tail hits, so
   fewer than five may be returned. Each stored row includes `summary` (first
   abstract sentence or a short fallback), `relevance_explanation`, `score`, and
   a PubMed `url`. No Claude call — mock hits when `MOCK_LLM=true` or if PubMed
   is unreachable.
4. **Map to reading plan** — `POST /api/strategies` with optional `spec_id`
   filters projects to spec-relevant papers (`spec_strategy.projects_from_spec`),
   generates one reading strategy, then merges relevance onto each step
   (`attach_spec_mapping`: `spec_relevance`, `spec_score`, `spec_why`; core
   before supporting). Saved strategies store `spec_id` / `spec_title` and the
   plan carries the same fields for round-trip navigation in the SPA.

### Paper groups (cross-project shelf organization)

The **Groups** view calls `POST /api/groups` (`app/grouping.py`):

1. **Analyze** — Claude (or `heuristic_paper_groups` offline) returns a
   `PaperGroupingMap`: `groups` (non-overlapping `paper_keys` across projects)
   and `drops` (duplicate, redundant, weak_fit, outdated).
2. **Validate** — `complete_paper_groups` drops invalid keys, ensures each paper
   appears in at most one group, and enriches groups with `papers` display refs.
3. **Persist** — saved in `paper_groups` on the store until purge.

Offline heuristics: normalized-title duplicate detection across collections,
tag/title clustering into cross-project sets, weak-fit papers with little shelf
overlap suggested for archive.

### Reading schedule

After a plan is finalized, `reading_schedule.attach_reading_schedule` estimates
minutes per paper (heuristic page count from tags/abstract/type at **12 pages/h**)
and assigns `scheduled_day` values using a **2 h/day** budget. The plan gets a
`schedule` object (`total_minutes`, `total_hours`, `estimated_days`, `summary`).
See [USAGE.md](USAGE.md#reading-time-assumptions).

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
| `POST` | `/api/groups` | Group papers across projects (no duplication) + drop suggestions → job |
| `GET` | `/api/groups` | Latest paper grouping map |
| `POST` | `/api/strategies` | Generate a reading plan (`mode`, `goal`, `project_keys`, optional `spec_id`) → job |
| `GET` / `DELETE` | `/api/strategies[/{id}]` | List / delete saved plans |
| `POST` | `/api/specs` | Upload a spec (file or `text`) |
| `GET` / `DELETE` | `/api/specs[/{id}]` | List / fetch / delete specs |
| `POST` | `/api/specs/{id}/analyze` | Screen library; store only relevant papers → job |
| `POST` | `/api/specs/{id}/discover` | PubMed discovery; papers not in library → job |
| `GET` | `/api/jobs` | List jobs (`?active=true` for queued/running only) |
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
  discovery.py     PubMed query + external paper discovery
  grouping.py      cross-project paper sets + drop suggestions
  spec_strategy.py spec-relevant project filter + plan mapping
  reading_schedule.py per-paper estimates and day schedule
  static/          the single-page UI
scripts/           setup.sh, run.sh
tests/             API tests (offline)
docs/              this documentation
```
