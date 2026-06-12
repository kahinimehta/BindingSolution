<div align="center">

<img src="docs/banner.svg" alt="BindingSolution — your AI reading room" width="820" />

**Point it at your Zotero library and it makes sense of it.**

*Categorize collections, find cross-project threads, plan what to read, and get
paper suggestions for a project spec — locally, with Claude.*

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

**API billing:** Claude usage is billed to your Anthropic account (pay per token). Zotero sync and saved results are free to revisit. Spec screening calls Claude once per paper — see [docs/BILLING.md](docs/BILLING.md) for cost drivers and tips.

## Library layout

After sync, collections split into **active** (2+ papers) and **excluded** (reference only):

| Group | Examples | Analyzed? |
| --- | --- | --- |
| **Active** | Collections with 2+ papers | Yes |
| **Excluded** | Empty folders, single-paper collections, unfiled papers | No |

Excluded items appear in a separate section at the bottom of **Library**. Add papers or merge collections in Zotero, then re-sync.

<p align="center">
  <img src="docs/screenshots/library.svg" alt="Library view with KPI bar above active and excluded collections" width="920" />
</p>

## Persistence & reset

Data lives in `./data/library.json` (gitignored). `make run` picks up where you left off — no re-sync or re-analysis needed unless you want fresh results.

| Action | What it does |
| --- | --- |
| **Purge library** (in-app, sidebar) | Wipes local projects, categorizations, connections, reading plans, and specs. Your Zotero library is untouched. Sync or load the demo again afterward. |
| `make clean` | Removes `data/`, the virtualenv, and caches — full dev reset. Keeps `.env`. |
| `make setup` again | Reinstalls dependencies only — does **not** delete your library. |

## Features

Use any view in any order — nothing is sequential.

- **Zotero sync** — Web API or local Zotero 7; bundled demo library for trying without keys
- **Active vs excluded collections** — only folders with 2+ papers are used in analysis; empty, single-paper, and unfiled collections are shown separately for reference
- **Project categorization** — discipline, themes, methods, keywords, and summary per collection
- **Cross-project connections** — shared threads across projects and suggested groupings to read together
- **Reading strategies** — pick projects (or let the agent choose), set a goal, get an ordered reading path with synthesis prompts; saved plans persist across sessions
- **Project-spec paper suggestions** — two tabs on **Project specs**:
  - **Upload & manage** — drop a PDF, Word (`.doc`/`.docx`), Markdown, or text spec. Irrelevant uploads (shopping lists, published papers, admin docs) are rejected with guidance.
  - **Suggested papers** — **Find relevant papers** screens your active library and lists only **core** and **supporting** hits, each with a short **why it's relevant** note. Runtime scales with library size; you can keep using the app while it runs.
- **Purge library** — start from scratch without touching Zotero (sidebar → **Purge library**)

<p align="center">
  <img src="docs/screenshots/strategies.svg" alt="Reading strategies compose form" width="920" />
</p>

<p align="center">
  <img src="docs/screenshots/specs-upload.svg" alt="Project specs Upload and manage tab" width="920" />
  <br /><br />
  <img src="docs/screenshots/specs.svg" alt="Project specs Suggested papers tab" width="920" />
</p>

## Docs

- [docs/USAGE.md](docs/USAGE.md) · [docs/CONFIGURATION.md](docs/CONFIGURATION.md) · [docs/BILLING.md](docs/BILLING.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- `make setup` · `make run` · `make dev` · `make test`

## License

MIT — see [LICENSE](LICENSE).
