# Configuration

All configuration lives in a single **`.env`** file at the repo root. It is
listed in `.gitignore` and **never committed** — `make setup` creates it for
you from `.env.example` (and `chmod 600`s it). Edit it with any editor:

```bash
${EDITOR:-nano} .env
```

After changing `.env`, restart the server (`Ctrl-C`, then `make run`).

---

## Getting your keys

### Claude API key (`ANTHROPIC_API_KEY`)

Powers AI features (categorization, connections, groups, **Chat**, strategies,
**Find in library** spec screening). Without it the app runs in a deterministic
demo mode.

**Billing:** usage is charged to **your Anthropic account** (input + output
tokens per API call). BindingSolution itself is free. Library spec screening is
the main cost driver on first run — it calls Claude once per paper in your
active library. **Re-screen library** is incremental (new papers only after a
sync). **PubMed discovery** does not use your Anthropic key. See [BILLING.md](BILLING.md)
for what costs money and how to use the API wisely.

1. Go to <https://console.anthropic.com/settings/keys>
2. Create a key, copy it (starts with `sk-ant-`)
3. Put it in `.env`: `ANTHROPIC_API_KEY=sk-ant-...`
4. Optional: set a monthly spend limit at
   <https://console.anthropic.com/settings/billing>

### Zotero — two ways

**Option A — Web API (works anywhere):**

1. Go to <https://www.zotero.org/settings/keys>
2. Your numeric **userID** is shown there → `ZOTERO_LIBRARY_ID`
3. Click *Create new private key*, give it **read-only** access →
   `ZOTERO_API_KEY`
4. Leave `ZOTERO_LIBRARY_TYPE=user` (use `group` + the group ID for a group
   library)

**Option B — local Zotero 7 app (no key needed):**

1. In Zotero: **Settings → Advanced → "Allow other applications on this
   computer to communicate with Zotero"**
2. In `.env`: `ZOTERO_LOCAL=true` and `ZOTERO_LIBRARY_ID=0`
3. Keep Zotero running while you sync.

> Live Zotero sync needs the optional `pyzotero` package. `make setup`
> installs it best-effort; if it was skipped, run
> `.venv/bin/pip install -r requirements-zotero.txt`. The demo library and all
> AI features work without it.

---

## All settings

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Claude API key. Unset → demo AI mode. |
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Model used for all analysis. Faster/cheaper models can lower cost — see [BILLING.md](BILLING.md). |
| `ZOTERO_LIBRARY_ID` | — | Your Zotero userID (or group ID). |
| `ZOTERO_API_KEY` | — | Read-only Zotero API key. |
| `ZOTERO_LIBRARY_TYPE` | `user` | `user` or `group`. |
| `ZOTERO_LOCAL` | `false` | Use the local Zotero 7 app instead of the Web API. |
| `HOST` | `127.0.0.1` | Bind address (keep local unless you know why). |
| `PORT` | `8765` | Server port. |
| `BINDING_DATA_DIR` | `./data` | Where synced library + analyses are stored (gitignored). |
| `MOCK_LLM` | `false` | Force demo AI even when a key is set (handy for UI work/tests). |

---

## Where your data lives

Everything synced and generated is written to `./data/library.json`
(or `$BINDING_DATA_DIR`). That directory is gitignored.

To start fresh:

- **In the app:** top toolbar → **Purge library** (wipes the JSON store; Zotero is untouched)
- **In the app:** top toolbar → **Sync library** (reads your Zotero collections and papers into the JSON store; refreshes local project lists and keeps categorizations for collections that still exist — does not modify Zotero or call Claude)
- **On disk:** delete `./data/` or run `make clean` (also removes the virtualenv)
- **`make setup` again** only reinstalls dependencies — it does not delete your library

Long-running work (sync, categorization, spec screening, etc.) runs as background
jobs. Use the sidebar **Running** dropdown to monitor progress after closing the
progress window or reloading the page. The dropdown opens upward with an opaque
background so multiple jobs stay readable. Close the progress popup **✕** to keep
working — that does not cancel the job. To cancel, open **Running** and click **✕**
on the active job row (cooperative; may wait for the current API call to finish).
Stopping the server (Ctrl+C) aborts all jobs immediately. Progress bars are
**indeterminate** when a step is one
long operation that cannot be split (single Claude call or PubMed search):
categorize one project, design a reading plan, discover on PubMed, load demo
library, and the **analyze** step of **Find connections** and **Group papers**
(prepare → analyze → apply). **Group papers** streams structured output at 32k
`max_tokens` — large shelves can run several minutes; keep the server running.
**Linear** jobs show `current/total` or *Step N of M*: Zotero sync per
collection, **Categorize all** per project (indeterminate while each project is
categorized), and spec screening per paper. Indeterminate steps show a full bar
and **Done** when they finish. After a run,
the server enforces **≥90% grouped** (minimum 10 papers per set, no maximum,
varied set sizes — not uniform chunks or mega-sets).

After pulling updates, **restart** the server (`Ctrl+C`, then `make run`) so new
API routes and `GET /api/status` `capabilities` (`chat`, `jobs_cancel`, etc.)
match the UI. **Chat** uses a large binding-green circular **↑** send button
(center-right of the compose box)
(bottom-right of the input). If chat endpoints 404, job cancel shows a restart toast, or
grouping shows *Streaming is required*, an old process is usually still bound to
port 8765.

Nothing is sent anywhere except the Anthropic API (for analysis) and Zotero
(to read your library). The server binds to `127.0.0.1` by default, so it's
only reachable from your own machine.

## Display

On wide monitors the UI is a **centered panel** (max width about 19200px, or
viewport minus 0.5rem) with cream margins on the sides. Base typography and
layout spacing are scaled **3×** for large / high-DPI displays — not browser
zoom. Key values in `app/static/styles.css` (not `.env`):

| Token | Approx. value | Role |
| --- | --- | --- |
| `html` `font-size` | `clamp(54px … 66px)` | Root type scale (all `rem` text) |
| `--app-max` | `min(19200px, 100vw − 0.5rem)` | Centered shell width |
| `--rail-w` | `864px` | Green sidebar width |

Project cards and nav labels wrap to their full height instead of clipping with
an inner scroll box. Fonts: **Montserrat** (headings / hero titles) and
**Hanken Grotesk** (body UI), via `--font-display` and `--font-body` in
`app/static/styles.css`.
