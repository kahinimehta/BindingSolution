<div align="center">

<img src="docs/banner.svg" alt="BindingSolution — your AI reading room" width="820" />

**Point it at your Zotero library and it makes sense of it.**

*Categorize collections, find cross-project threads, plan what to read, and score
papers against a project spec — locally, with Claude.*

</div>

---

## Quick start

```bash
git clone https://github.com/kahinimehta/bindingsolution.git
cd bindingsolution
make setup && make run    # → http://127.0.0.1:8765
```

Add keys to the gitignored `.env` created by setup (`ANTHROPIC_API_KEY`, `ZOTERO_LIBRARY_ID`, `ZOTERO_API_KEY`). See [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

**No keys?** `make run` → **Load demo library**. Everything works on bundled sample data.

## Library layout

After sync, collections split into **active** (2+ papers) and **excluded** (reference only):

| Group | Examples | Analyzed? |
| --- | --- | --- |
| **Active** | Collections with 2+ papers | Yes |
| **Excluded** | Empty folders, single-paper collections, unfiled papers | No |

Excluded items appear in a separate section at the bottom of **Library**. Add papers or merge collections in Zotero, then re-sync.

<p align="center">
  <img src="docs/screenshots/library.svg" alt="Library view with active projects and excluded collections" width="900" />
</p>

## Persistence

Data lives in `./data/library.json` (gitignored). `make run` picks up where you left off — no re-sync or re-analysis needed unless you want fresh results. `make clean` wipes everything.

## Features

- **Project categorization** — discipline, themes, methods, summary per collection
- **Cross-project connections** — shared threads and suggested groupings
- **Reading strategies** — ordered paths with synthesis prompts
- **Project-spec matching** — score and summarize every paper against your aim
- **Zotero sync** — Web API or local Zotero 7; demo library included

## Docs

- [docs/USAGE.md](docs/USAGE.md) · [docs/CONFIGURATION.md](docs/CONFIGURATION.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- `make setup` · `make run` · `make dev` · `make test`

## License

MIT — see [LICENSE](LICENSE).
