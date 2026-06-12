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

Powers AI features (categorization, connections, strategies, **Find in library**
spec screening). Without it the app runs in a deterministic demo mode.

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
jobs. Use the sidebar **Running** panel to monitor progress after closing the
progress window or reloading the page. Only stopping the server (e.g. Ctrl+C)
cancels in-flight jobs. **Group papers** uses phase-based progress (prepare →
analyze → apply) with an indeterminate bar during the single Claude call; per-paper
jobs (sync, spec screening) show `current/total` counts instead.

Nothing is sent anywhere except the Anthropic API (for analysis) and Zotero
(to read your library). The server binds to `127.0.0.1` by default, so it's
only reachable from your own machine.

## Display

On wide monitors the UI is a **centered panel** (max width about 19200px, or
viewport minus 0.5rem) with cream margins on the sides. Base typography and
layout spacing are scaled for large / high-DPI displays (`html` root font-size and
`--app-max`, `--rail-w` in `app/static/styles.css`), not in `.env`.
