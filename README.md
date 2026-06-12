<div align="center">

<img src="docs/banner.svg" alt="BindingSolution — your AI reading room" width="820" />

**Point it at your Zotero library and it makes sense of it.**

*Literature-review simplifier: categorize projects, find what connects them,
plan what to read, and match papers to whatever you're working on.*

</div>

---

## Purpose

A personal research library is a pile of folders and PDFs you half-remember.
BindingSolution reads your Zotero collections with Claude and turns them into
something you can actually navigate: it labels each project, surfaces the
threads that run across them, builds you an ordered reading plan, and — when
you drop in a project spec — tells you how each paper is relevant and
summarizes it. It all runs locally with a pretty web UI.

## Quick start

Paste this into your terminal. It sets up everything, creates a **gitignored
`.env`** for your keys, and starts the app:

```bash
git clone https://github.com/kahinimehta/bindingsolution.git
cd bindingsolution
make setup          # venv + deps, and copies .env.example → .env (gitignored, chmod 600)

# add your keys to the .env that was just created (never committed):
printf '\nANTHROPIC_API_KEY=sk-ant-...\n'   >> .env   # https://console.anthropic.com/settings/keys
printf 'ZOTERO_LIBRARY_ID=1234567\n'        >> .env   # https://www.zotero.org/settings/keys
printf 'ZOTERO_API_KEY=...\n'               >> .env   # (read-only key from the same page)

make run            # → http://127.0.0.1:8765
```

Prefer an editor? `make setup` then `${EDITOR:-nano} .env`, then `make run`.

**No keys yet?** Still run `make setup && make run`, open the app, and click
**Load demo library** — every feature works on bundled sample data (Claude
features fall back to a heuristic until you add a key). Your `.env` is in
`.gitignore` and never reaches GitHub.

## Does it remember my work?

Yes. Everything is saved locally to `./data/library.json` (gitignored) and
survives stopping and restarting the server. You do **not** need to re-sync or
re-run analyses every time you open the app.

| Command | What it does | Wipes your library / analyses? |
| --- | --- | --- |
| `make setup` | Creates `.venv`, installs deps, scaffolds `.env` if missing | No |
| `make run` | Starts the server at http://127.0.0.1:8765 | No |
| `make dev` | Same as `make run`, with auto-reload for code changes | No |
| `make test` | Runs the offline test suite | No |
| `make clean` | Removes `.venv`, caches, and the `data/` folder | **Yes** |

**What persists between sessions:** synced projects and papers, categorizations,
connection maps, reading strategies, and project-spec analyses.

**When to re-run something:**

- **Sync library** — when you want fresh papers from Zotero (existing
  categorizations for collections that still exist are kept).
- **Categorize / Find connections / Analyze spec** — only when you want new AI
  output, or after a big library change.
- **After `make clean`** — start over: sync (or load the demo) and run analyses again.

Override the data location with `BINDING_DATA_DIR` in `.env` if you want the
store somewhere other than `./data/`. See [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Features

- **📂 Project categorization** — each Zotero collection is labeled with its
  discipline, themes, methods, and a short summary. One click does the whole shelf.
- **⁂ Cross-project connections** — finds shared concepts, methods, and authors
  that thread through different projects, and suggests which to combine.
- **↯ Reading strategies** — pick projects to combine (or let the agent decide)
  and get an ordered, foundational-first reading path with synthesis prompts.
- **✦ Project-spec matching** — drop in a spec, grant aim, or paragraph (PDF /
  Markdown / text or paste); every paper is **summarized** and **scored** for
  how it's relevant to *that* project.
- **🗂 Zotero sync** — works with the Zotero Web API or a local Zotero 7 app.
  No library? A built-in **demo library** makes everything explorable offline.
- **🔌 Offline-friendly** — runs without a Claude key in a deterministic demo
  mode, so the UI and tests work anywhere.
- **🎨 Pretty local UI** — a single-page "clothbound book" interface; live
  progress on every analysis; nothing leaves your machine.

## Docs

- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) — every setting + where to get keys
- [docs/USAGE.md](docs/USAGE.md) — a walkthrough of each feature
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how it's built, API reference
- `make help`-style targets: `make setup` · `make run` · `make dev` · `make test`

## License

MIT — see [LICENSE](LICENSE).
