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

Powers every AI feature (categorization, connections, strategies, paper
suggestions). Without it the app runs in a deterministic demo mode.

1. Go to <https://console.anthropic.com/settings/keys>
2. Create a key, copy it (starts with `sk-ant-`)
3. Put it in `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

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
| `ANTHROPIC_MODEL` | `claude-opus-4-8` | Model used for all analysis. |
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
(or `$BINDING_DATA_DIR`). That directory is gitignored. Delete it to start
fresh; `make clean` removes it along with the virtualenv.

Nothing is sent anywhere except the Anthropic API (for analysis) and Zotero
(to read your library). The server binds to `127.0.0.1` by default, so it's
only reachable from your own machine.
